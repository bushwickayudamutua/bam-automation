const { requestIds, furnRequestIds, ssRequestIds, meshRequestIds } = input.config();

// Retrieve tables
const reqTable = base.getTable('Requests');
const furnReqTable = base.getTable('Furniture Requests');
const ssReqTable = base.getTable('Social Service Requests');
const meshTable = base.getTable('Mesh Requests');
const countTable = base.getTable('Fulfilled Request Count');

const countCols = countTable.fields;
let allCounts = null;
const dateRecordPromises = new Map();

function dateKey(value) {
  if (value == null) return null;
  if (value instanceof Date) {
    return value.toISOString().slice(0, 10);
  }
  const text = String(value).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) {
    return text.slice(0, 10);
  }
  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed.toISOString().slice(0, 10);
}

async function getAllCounts() {
  if (allCounts === null) {
    allCounts = (await countTable.selectRecordsAsync({ fields: countCols })).records;
  }
  return allCounts;
}

async function findOrCreateCountRecord(date) {
  const key = dateKey(date);
  if (key == null) return null;

  if (!dateRecordPromises.has(key)) {
    dateRecordPromises.set(key, (async () => {
      const counts = await getAllCounts();
      for (const count of counts) {
        if (dateKey(count.getCellValue('Date')) === key) return count;
      }

      const recId = await countTable.createRecordAsync({ Date: key });
      const rec = await countTable.selectRecordAsync(recId, { fields: countCols });
      if (rec === null) throw "Airtable is broken";
      counts.push(rec);
      return rec;
    })());
  }

  return dateRecordPromises.get(key);
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
    const date = dateKey(req.getCellValue('Status Last Updated At'));
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
    const date = dateKey(req.getCellValue('Status Last Updated At'));
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
  processRequests(furnReqTable, furnRequestIds, { }),
  processRequests(ssReqTable, ssRequestIds, { }),
  processMesh(meshTable, meshRequestIds),
]);
