const { requestIds, ssRequestIds, meshRequestIds } = input.config();

// Retrieve tables
const reqTable = base.getTable('Requests');
const ssReqTable = base.getTable('Social Service Requests');
const meshTable = base.getTable('Mesh Requests');
const countTable = base.getTable('Fulfilled Request Count');

const countCols = countTable.fields;
let allCounts = null;
const dateRecordPromises = new Map();

// Normalize an Airtable date/dateTime cell value (string or Date) to a
// stable date-only `YYYY-MM-DD` key. This keeps grouping and the count
// table's Date lookup consistent, avoiding both time-of-day bucket splits
// and comparisons that never match across value types.
function toDateKey(value) {
  if (value == null) return null;
  const iso = typeof value === 'string' ? value : value.toISOString();
  return iso.slice(0, 10);
}

async function getAllCounts() {
  if (allCounts === null) {
    allCounts = (await countTable.selectRecordsAsync({ fields: countCols })).records;
  }
  return allCounts;
}

async function findOrCreateCountRecord(date) {
  if (date == null) return null;

  if (!dateRecordPromises.has(date)) {
    dateRecordPromises.set(date, (async () => {
      const counts = await getAllCounts();
      for (const count of counts) {
        if (toDateKey(count.getCellValue('Date')) === date) return count;
      }

      const recId = await countTable.createRecordAsync({ 'Date': date });
      const rec = await countTable.selectRecordAsync(recId, { fields: countCols });
      if (rec === null) throw "Airtable is broken";
      counts.push(rec);
      return rec;
    })());
  }

  return dateRecordPromises.get(date);
}

async function processRequests(table, reqIds, columnOverwrites) {
  if (!reqIds?.length) return;

  const groups = {};

  const reqs = (await table.selectRecordsAsync({ recordIds: reqIds, fields: [
    'Status',
    'Status Last Updated At',
    'Type',
  ] })).records;
  for (const req of reqs) {
    const date = toDateKey(req.getCellValue('Status Last Updated At'));
    if (date == null) continue;

    groups[date] ??= [];
    groups[date].push(req);
  }

  function getCountCol(reqType) {
    return columnOverwrites[reqType] ?? reqType.split(' / ')[1];
  }

  for (const [date, reqs] of Object.entries(groups)) {
    const fields = {};
    const countRec = await findOrCreateCountRecord(date);
    if (countRec == null) continue;

    for (const req of reqs) {
      const reqStatus = req.getCellValue('Status').name;
      if (reqStatus === 'Delivered') {
        const reqType = req.getCellValue('Type').name;
        const countCol = getCountCol(reqType);
        if (!countCol) continue;

        fields[countCol] ??= countRec.getCellValue(countCol);
        fields[countCol]++;
      }
    }

    if (Object.keys(fields).length) {
      await countTable.updateRecordAsync(countRec, fields);
    }

    for (let idx = 0; idx < reqs.length; idx += 50) {
      await table.deleteRecordsAsync(reqs.slice(idx, idx + 50));
    }
  }
}

async function processMesh(table, reqIds) {
  if (!reqIds?.length) return;

  const countCol = 'Low-Cost Home Internet';
  const groups = {};

  const reqs = (await table.selectRecordsAsync({ recordIds: reqIds, fields: [
    'Status',
    'Status Last Updated At',
    'Phone Number (from Household)',
  ] })).records;
  for (const req of reqs) {
    const date = toDateKey(req.getCellValue('Status Last Updated At'));
    if (date == null) continue;

    groups[date] ??= [];
    groups[date].push(req);
  }

  for (const [date, reqs] of Object.entries(groups)) {
    const fields = {};
    const countRec = await findOrCreateCountRecord(date);
    if (countRec == null) continue;
    const countedPhones = new Set();

    for (const req of reqs) {
      const reqStatus = req.getCellValue('Status').name;
      if (reqStatus !== 'YAY! MESH INSTALLED!') continue;

      const phoneRaw = req.getCellValue('Phone Number (from Household)');
      const phone = Array.isArray(phoneRaw) ? phoneRaw[0] : phoneRaw;
      if (!phone || countedPhones.has(phone)) continue;

      countedPhones.add(phone);
      fields[countCol] ??= countRec.getCellValue(countCol);
      fields[countCol]++;
    }

    if (Object.keys(fields).length) {
      await countTable.updateRecordAsync(countRec, fields);
    }

    // Delete records in group in pages of 50
    for (let idx = 0; idx < reqs.length; idx += 50) {
      await table.deleteRecordsAsync(reqs.slice(idx, idx + 50));
    }
  }
}

await Promise.all([
  processRequests(reqTable, requestIds, { }),
  processRequests(ssReqTable, ssRequestIds, { }),
  processMesh(meshTable, meshRequestIds),
]);
