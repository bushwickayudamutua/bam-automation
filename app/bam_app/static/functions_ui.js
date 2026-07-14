const state = {
  functions: [],
  selected: null,
};

const el = {
  apikey:           document.getElementById("apikey"),
  loadFunctionsBtn: document.getElementById("loadFunctionsBtn"),
  functionSelect:   document.getElementById("functionSelect"),
  functionDesc:     document.getElementById("functionDesc"),
  paramsContainer:  document.getElementById("paramsContainer"),
  runBtn:           document.getElementById("runBtn"),
  resetBtn:         document.getElementById("resetBtn"),
  statusLine:       document.getElementById("statusLine"),
  responseBox:      document.getElementById("responseBox"),
  logsBox:          document.getElementById("logsBox"),
  errorBox:         document.getElementById("errorBox"),
};

function setStatus(message, tone = "warn") {
  el.statusLine.textContent = message;
  el.statusLine.className = `status-line ${tone}`;
}

function pretty(value) {
  return JSON.stringify(value, null, 2);
}

function renderLogs(lines) {
  if (!Array.isArray(lines) || lines.length === 0) return "(no logs)";
  return lines.map((entry) => {
    if (typeof entry === "string") return entry;
    const level = (entry.level || "info").toUpperCase().padEnd(9);
    const msg = entry.message ?? JSON.stringify(entry);
    return `${level} ${msg}`;
  }).join("\n");
}

function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function parseType(baseType, rawValue) {
  if (rawValue === "" || rawValue === null || rawValue === undefined) return null;

  if (baseType === "int") {
    const n = Number(rawValue);
    if (!Number.isInteger(n)) throw new Error(`Expected integer, got ${rawValue}`);
    return n;
  }

  if (baseType === "float") {
    const n = Number(rawValue);
    if (Number.isNaN(n)) throw new Error(`Expected number, got ${rawValue}`);
    return n;
  }

  if (baseType === "bool") {
    if (typeof rawValue === "boolean") return rawValue;
    const v = String(rawValue).toLowerCase();
    if (["true", "1", "yes", "y"].includes(v)) return true;
    if (["false", "0", "no", "n"].includes(v)) return false;
    throw new Error(`Expected boolean, got ${rawValue}`);
  }

  if (baseType === "json") {
    if (typeof rawValue === "object") return rawValue;
    return JSON.parse(rawValue);
  }

  if (baseType.endsWith("_list")) {
    const itemType = baseType.replace("_list", "");
    return String(rawValue).split(",").map((v) => v.trim()).filter(Boolean)
      .map((item) => parseType(itemType, item));
  }

  return rawValue;
}

function inputTypeForParam(typeName) {
  if (typeName === "int" || typeName === "float") return "number";
  if (typeName === "datetime") return "datetime-local";
  return "text";
}

function renderParams(schema) {
  const keys = Object.keys(schema || {});
  if (!keys.length) {
    el.paramsContainer.innerHTML = '<p class="param-hint">No params required.</p>';
    el.runBtn.disabled = false;
    el.resetBtn.disabled = false;
    return;
  }

  el.paramsContainer.innerHTML = keys.map((name) => {
    const param = schema[name] || {};
    const type = param.type || "string";
    const description = param.description || "";
    const required = !!param.required;
    const defaultValue = param.default;

    if (type === "bool") {
      const checked = defaultValue === true ? "checked" : "";
      return `
        <div class="param-card">
          <label class="checkbox-row">
            <input data-param-name="${escapeHtml(name)}" data-param-type="${escapeHtml(type)}" type="checkbox" ${checked} />
            <span>${escapeHtml(name)} (bool)</span>
          </label>
          <div class="param-hint">${required ? "Required" : "Optional"}${description ? ` · ${escapeHtml(description)}` : ""}</div>
        </div>`;
    }

    const isJson = type === "json";
    const isList = type.endsWith("_list");
    const placeholder = defaultValue !== null && defaultValue !== undefined
      ? String(defaultValue)
      : isJson ? '{\n  "key": "value"\n}' : isList ? "item1,item2,item3" : "";
    const val = defaultValue !== null && defaultValue !== undefined
      ? escapeHtml(String(defaultValue)) : "";

    const input = isJson
      ? `<textarea data-param-name="${escapeHtml(name)}" data-param-type="${escapeHtml(type)}" placeholder="${escapeHtml(placeholder)}"></textarea>`
      : `<input data-param-name="${escapeHtml(name)}" data-param-type="${escapeHtml(type)}" type="${inputTypeForParam(type)}" placeholder="${escapeHtml(placeholder)}" value="${val}" />`;

    return `
      <div class="param-card">
        <label>${escapeHtml(name)} (${escapeHtml(type)})</label>
        ${input}
        <div class="param-hint">${required ? "Required" : "Optional"}${description ? ` · ${escapeHtml(description)}` : ""}</div>
      </div>`;
  }).join("\n");

  el.runBtn.disabled = false;
  el.resetBtn.disabled = false;
}

function collectParams() {
  const payload = {};
  el.paramsContainer.querySelectorAll("[data-param-name]").forEach((node) => {
    const name = node.dataset.paramName;
    const type = node.dataset.paramType;
    const value = node.type === "checkbox" ? node.checked : node.value;
    if (node.type !== "checkbox" && String(value).trim() === "") return;
    payload[name] = parseType(type, value);
  });
  return payload;
}

function updateFunctionSelect() {
  const options = state.functions.map(
    (f) => `<option value="${escapeHtml(f.function_name)}">${escapeHtml(f.function_name)}</option>`
  );
  el.functionSelect.innerHTML = options.length
    ? options.join("\n")
    : '<option value="">No functions found</option>';
  el.functionSelect.disabled = options.length === 0;

  if (options.length > 0) {
    el.functionSelect.value = state.functions[0].function_name;
    state.selected = state.functions[0];
    el.functionDesc.textContent = state.selected.description || "";
    renderParams(state.selected.params || {});
  } else {
    state.selected = null;
    el.paramsContainer.innerHTML = "";
    el.runBtn.disabled = true;
    el.resetBtn.disabled = true;
  }
}

async function loadFunctions() {
  const apikey = el.apikey.value.trim();
  if (!apikey) { setStatus("API key is required.", "err"); return; }

  setStatus("Loading functions…", "warn");
  el.loadFunctionsBtn.disabled = true;

  try {
    const res = await fetch(`/functions?apikey=${encodeURIComponent(apikey)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data?.detail || `Failed (${res.status})`);

    state.functions = data.functions || [];
    updateFunctionSelect();

    if (data.load_errors?.length) {
      setStatus(`Loaded ${state.functions.length} function(s) — ${data.load_errors.length} error(s).`, "warn");
      el.errorBox.textContent = pretty(data.load_errors);
    } else {
      setStatus(`Loaded ${state.functions.length} function(s).`, "ok");
      el.errorBox.textContent = "null";
    }
  } catch (err) {
    setStatus(String(err.message || err), "err");
  } finally {
    el.loadFunctionsBtn.disabled = false;
  }
}

async function runSelectedFunction() {
  const apikey = el.apikey.value.trim();
  if (!apikey) { setStatus("API key is required.", "err"); return; }
  if (!state.selected) { setStatus("No function selected.", "err"); return; }

  let payload;
  try {
    payload = collectParams();
  } catch (err) {
    setStatus(`Invalid params: ${String(err.message || err)}`, "err");
    return;
  }

  setStatus(`Running ${state.selected.function_name}…`, "warn");
  el.runBtn.disabled = true;
  el.runBtn.classList.add("running");
  el.responseBox.textContent = "{}";
  el.logsBox.textContent = "(no logs)";
  el.errorBox.textContent = "(no error)";

  try {
    const res = await fetch(
      `/functions/${encodeURIComponent(state.selected.function_name)}?apikey=${encodeURIComponent(apikey)}`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }
    );
    const data = await res.json();

    if (!res.ok) {
      setStatus(`Function failed (${res.status}).`, "err");
      el.errorBox.textContent = data?.detail?.error ?? pretty(data.detail ?? data);
      if (data?.detail?.logs) el.logsBox.textContent = renderLogs(data.detail.logs);
      return;
    }

    setStatus("Function completed successfully.", "ok");
    el.responseBox.textContent = pretty(data.response ?? null);
    el.logsBox.textContent = renderLogs(data.logs ?? []);
  } catch (err) {
    setStatus(`Request error: ${String(err.message || err)}`, "err");
  } finally {
    el.runBtn.disabled = false;
    el.runBtn.classList.remove("running");
  }
}

function resetParams() {
  if (!state.selected) return;
  renderParams(state.selected.params || {});
  setStatus("Params reset to defaults.", "warn");
}

el.loadFunctionsBtn.addEventListener("click", loadFunctions);
el.runBtn.addEventListener("click", runSelectedFunction);
el.resetBtn.addEventListener("click", resetParams);
el.functionSelect.addEventListener("change", (event) => {
  const name = event.target.value;
  state.selected = state.functions.find((f) => f.function_name === name) || null;
  el.functionDesc.textContent = state.selected?.description || "";
  renderParams(state.selected?.params || {});
  setStatus(
    state.selected ? `Selected ${state.selected.function_name}.` : "No function selected.",
    state.selected ? "ok" : "warn"
  );
});

document.querySelectorAll(".copy-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    const target = document.getElementById(btn.dataset.target);
    if (!target) return;
    navigator.clipboard.writeText(target.textContent).then(() => {
      btn.textContent = "Copied!";
      btn.classList.add("copied");
      setTimeout(() => { btn.textContent = "Copy"; btn.classList.remove("copied"); }, 1500);
    });
  });
});
