const { requestIds, furnRequestIds, ssRequestIds, meshRequestIds } = input.config();

// Retrieve tables
const reqTable = base.getTable('Requests');
const furnReqTable = base.getTable('Furniture Requests');
const ssReqTable = base.getTable('Social Service Requests');
const meshTable = base.getTable('Mesh Requests');
const countTable = base.getTable('Fulfilled Request Count');

const invalidCountCols = new Set();
const uncountedRequestIds = [];

// 'Status Last Updated At' can read back as a Date object or ISO datetime string
// while 'Date' reads back as 'YYYY-MM-DD'; normalize both to a day-level key so
// grouping and the find-or-create comparison actually match. Days are bucketed
// in NY time, not the script server's timezone, so evening closes don't count
// toward the next day.
function toLocalDay(d) {
  try {
    return d.toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
  } catch (error) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }
}

function dateKey(value) {
  if (value == null) return null;
  if (value instanceof Date) return toLocalDay(value);
  const text = String(value).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) return text.slice(0, 10);
  const parsed = new Date(text);
  if (Number.isNaN(parsed.getTime())) return null;
  return toLocalDay(parsed);
}

const allCounts = (await countTable.selectRecordsAsync({
  fields: countTable.fields,
})).records;

async function findOrCreateCountRecord(date) {
  for (const count of allCounts) {
    if (dateKey(count.getCellValue('Date')) === date) return count;
  }

  const recId = await countTable.createRecordAsync({ Date: date });
  const rec = await countTable.selectRecordAsync(recId, { fields: countTable.fields });
  if (rec === null) throw "Airtable is broken";
  allCounts.push(rec);
  return rec;
}

async function processRequests(table, reqIds, getCountCol, deliveredStatus, getCountKey) {
  if (!reqIds?.length) return;

  // Step 1: group requests by date
  const requestGroups = new Map();

  const reqs = (await table.selectRecordsAsync({
    recordIds: reqIds,
    fields: table.fields,
  })).records;
  for (const req of reqs) {
    const date = dateKey(req.getCellValue('Status Last Updated At'));

    if (!requestGroups.has(date)) requestGroups.set(date, []);
    requestGroups.get(date).push(req);
  }

  // Step 2: process each group
  for (const [date, reqs] of requestGroups) {
    const fields = {};
    const countRec = await findOrCreateCountRecord(date);
    const countedKeys = new Set();

    const reqsToDelete = [];
    for (const req of reqs) {
      // Validate counter column
      const countCol = getCountCol(req);
      if (!countCol || !countTable.fields.find((field) => (field.name === countCol))) {
        invalidCountCols.add(countCol ?? '(empty Type)');
        uncountedRequestIds.push(req.id);
        continue;
      }

      // Bump counter if delivered; when a count key is defined, count at most
      // once per key per date (and skip records with no key at all)
      const reqStatus = req.getCellValue('Status')?.name;
      if (reqStatus === deliveredStatus) {
        let shouldCount = true;
        if (getCountKey) {
          const countKey = getCountKey(req);
          shouldCount = Boolean(countKey) && !countedKeys.has(countKey);
          if (countKey) countedKeys.add(countKey);
        }
        if (shouldCount) {
          fields[countCol] ??= countRec.getCellValue(countCol);
          fields[countCol]++;
        }
      }

      // Mark request for deletion
      reqsToDelete.push(req)
    }

    // Update counter
    if (Object.keys(fields).length) {
      await countTable.updateRecordAsync(countRec, fields);
    }

    // Delete marked requests in pages of 50
    for (let idx = 0; idx < reqsToDelete.length; idx += 50) {
      await table.deleteRecordsAsync(reqsToDelete.slice(idx, idx + 50));
    }
  }
}

function getCountColFromType(req) {
  const typeName = req.getCellValue('Type')?.name;
  // Fall back to the full name when there is no ' / ' separator so the
  // invalid-column report shows something identifiable
  return typeName?.split(' / ')[1] ?? typeName;
}

// Mesh installs count once per household phone per close date
const meshHasPhoneField = meshTable.fields.some(
  (field) => field.name === 'Phone Number (from Household)'
);
function getHouseholdPhone(req) {
  const phone = req.getCellValue('Phone Number (from Household)');
  return Array.isArray(phone) ? phone[0] : phone;
}

const DELIVERED_TAG = 'Delivered'

try {
  await processRequests(reqTable, requestIds, getCountColFromType, DELIVERED_TAG);
  await processRequests(furnReqTable, furnRequestIds, getCountColFromType, DELIVERED_TAG);
  await processRequests(ssReqTable, ssRequestIds, getCountColFromType, DELIVERED_TAG);
  await processRequests(
    meshTable,
    meshRequestIds,
    () => 'Low-Cost Home Internet',
    'YAY! MESH INSTALLED!',
    meshHasPhoneField ? getHouseholdPhone : undefined,
  );
} finally {
  // Report even if a later table's processing throws
  output.set('invalidCountCols', [...invalidCountCols]);
  output.set('uncountedRequestIds', uncountedRequestIds);
}
