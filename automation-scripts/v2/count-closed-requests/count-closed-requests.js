const { requestIds, furnRequestIds, ssRequestIds, meshRequestIds } = input.config();

const DELIVERED_TAG = 'Delivered'

// Retrieve tables
const reqTable = base.getTable('Requests');
const furnReqTable = base.getTable('Furniture Requests');
const ssReqTable = base.getTable('Social Service Requests');
const meshTable = base.getTable('Mesh Requests');
const countTable = base.getTable('Fulfilled Request Count');

const invalidCountCols = new Set();

async function processRequests(table, reqIds, getCountCol) {
  if (!reqIds.length) return;

  // Step 1: pull all count records, define find-or-create util
  const allCounts = (await countTable.selectRecordsAsync({
    fields: countTable.fields,
  })).records;

  async function findOrCreateCountRecord(date) {
    for (const count of allCounts) {
      if (count.getCellValue('Date') === date) return count;
    }

    const recId = await countTable.createRecordAsync({ Date: date });
    const rec = await countTable.selectRecordAsync(recId, { fields: countTable.fields });
    if (rec === null) throw "Airtable is broken";
    return rec;
  }

  // Step 2: group requests by date
  const requestGroups = new Map();

  for (let idx = 0; idx < reqIds.length; idx += 100) {
    const reqs = (await table.selectRecordsAsync({
      recordIds: reqIds.slice(idx, idx + 100),
      fields: table.fields,
    })).records;
    for (const req of reqs) {
      const date = req.getCellValue('Status Last Updated At');

      if (!requestGroups.has(date)) requestGroups.set(date, []);
      requestGroups.get(date).push(req);
    }
  }

  // Step 3: process each group
  for (const [date, reqs] of requestGroups) {
    // Aggregate count updates
    const countUpdates = {};

    const reqsToDelete = [];
    for (const req of reqs) {
      // Validate counter column
      const countCol = getCountCol(req);
      if (!countTable.fields.find((field) => (field.name === countCol))) {
        invalidCountCols.add(countCol);
        continue;
      }

      // Bump counter if delivered
      const reqStatus = req.getCellValue('Status').name;
      if (reqStatus === DELIVERED_TAG) {
        countUpdates[countCol] ??= 0;
        countUpdates[countCol]++;
      }

      // Mark request for deletion
      reqsToDelete.push(req)
    }

    // Write updates to count table
    if (Object.keys(countUpdates).length >= 0) {
      const countRec = await findOrCreateCountRecord(date);
      for (const countCol of Object.keys(countUpdates)) {
        countUpdates[countCol] += countRec.getCellValue(countCol);
      }
      await countTable.updateRecordAsync(countRec, countUpdates);
    }

    // Delete marked requests in pages of 50
    for (let idx = 0; idx < reqsToDelete.length; idx += 50) {
      await table.deleteRecordsAsync(reqsToDelete.slice(idx, idx + 50));
    }
  }
}

function getCountColFromType(req) {
  return req.getCellValue('Type').name.split(' / ')[1];
}

await processRequests(reqTable, requestIds, getCountColFromType);
await processRequests(furnReqTable, furnRequestIds, getCountColFromType);
await processRequests(ssReqTable, ssRequestIds, getCountColFromType);
await processRequests(meshTable, meshRequestIds, () => 'Low-Cost Home Internet');

output.set('invalidCountCols', [...invalidCountCols]);
