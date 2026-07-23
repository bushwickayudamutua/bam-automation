const { requestIds, furnRequestIds, ssRequestIds, meshRequestIds } = input.config();

// Retrieve tables
const reqTable = base.getTable('Requests');
const furnReqTable = base.getTable('Furniture Requests');
const ssReqTable = base.getTable('Social Service Requests');
const meshTable = base.getTable('Mesh Requests');
const countTable = base.getTable('Fulfilled Request Count');

async function processRequests(table, reqIds, getCountCol, deliveredStatus) {
  // Step 1: pull all count records, define find-or-create util
  const countCols = countTable.fields;
  const allCounts = (await countTable.selectRecordsAsync({ fields: countCols })).records;

  async function findOrCreateCountRecord(date) {
    for (const count of allCounts) {
      if (count.getCellValue('Date') === date) return count;
    }
  
    const recId = await countTable.createRecordAsync({ 'Date': date });
    const rec = await countTable.selectRecordAsync(recId, { fields: countCols });
    if (rec === null) throw "Airtable is broken";
    return rec;
  }

  // Step 2: group requests by date and type
  const groups = {};

  const reqs = (await table.selectRecordsAsync({
    recordIds: reqIds,
    fields: table.fields,
  })).records;
  for (const req of reqs) {
    const date = req.getCellValue('Status Last Updated At');

    groups[date] ??= [];
    groups[date].push(req);
  }

  // Step 3: process each group
  for (const [date, reqs] of Object.entries(groups)) {
    const fields = {};
    const countRec = await findOrCreateCountRecord(date);

    for (const req of reqs) {
      const reqStatus = req.getCellValue('Status').name;
      if (reqStatus === deliveredStatus) {
        const countCol = getCountCol(req);
        if (!countCol) continue;

        fields[countCol] ??= countRec.getCellValue(countCol);
        fields[countCol]++;
      }
    }

    // Update counter
    await countTable.updateRecordAsync(countRec, fields);

    // Delete records in group in pages of 50
    for (let idx = 0; idx < reqs.length; idx += 50) {
      await table.deleteRecordsAsync(reqs.slice(idx, idx + 50));
    }
  }
}

function getCountColFromType(req) {
  return req.getCellValue('Type').name.split(' / ')[1];
}

const DELIVERED_TAG = 'Delivered'

await processRequests(reqTable, requestIds, getCountColFromType, DELIVERED_TAG);
await processRequests(furnReqTable, furnRequestIds, getCountColFromType, DELIVERED_TAG);
await processRequests(ssReqTable, ssRequestIds, getCountColFromType, DELIVERED_TAG);
await processRequests(meshTable, meshRequestIds, () => 'Low-Cost Home Internet', 'YAY! MESH INSTALLED!');
