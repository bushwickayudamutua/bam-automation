const { requestIds, ssRequestIds } = input.config();

// Retrieve tables
const reqTable = base.getTable('Requests');
const ssReqTable = base.getTable('Social Service Requests');
const countTable = base.getTable('Fulfilled Request Count');

async function processRequests(table, reqIds, columnOverwrites) {
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

  const reqs = (await table.selectRecordsAsync({ recordIds: reqIds, fields: [
    'Status',
    'Status Last Updated At',
    'Type',
  ] })).records;
  for (const req of reqs) {
    const date = req.getCellValue('Status Last Updated At');

    groups[date] ??= [];
    groups[date].push(req);
  }

  // Step 3: process each group 

  // Helper function to convert request type to counter column
  function getCountCol(reqType) {
    return columnOverwrites[reqType] ?? reqType.split(' / ')[1];
  }

  for (const [date, reqs] of Object.entries(groups)) {
    const fields = {};
    const countRec = await findOrCreateCountRecord(date);

    for (const req of reqs) {
      const reqStatus = req.getCellValue('Status').name;
      if (reqStatus === 'Delivered') {
        const reqType = req.getCellValue('Type').name;
        const countCol = getCountCol(reqType);

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

await Promise.all([
  processRequests(reqTable, requestIds, {
    "Bastidor individual / Twin Bed Frame 單人床架": "Twin Bed Frame",
    "Comida caliente / Hot meals / 热食": "Hot Meals",
  }),
  processRequests(ssReqTable, ssRequestIds, {
    "Asistencia legal de inquilinos / Tenant legal assistance / 租戶法律協助":
      "Tenant Legal Assistance",
    "Asistencia con servicios escolares / Assistance with in-school services / 學校服務協助":
      "Assistance with In-School Services",
    "Tutoría estudiantil / Tutoring for students / 學生輔導":
      "Tutoring for Students",
    "Asistencia asegurando vivienda/ Securing housing / 住房協助":
      "Assistance Securing Housing",
    "Asistencia con seguro médico / Medical insurance support / 醫療保險協助":
      "Medical Insurance Support",
    "Internet de bajo costo en casa / Low-Cost Internet at home / 網絡連結協助":
      "Low-Cost Home Internet",
    "Asistencia con beneficios de comida / Assistance with food benefits / 食品福利協助 (WIC, SNAP, P-EBT)":
      "Assistance with Food Benefits",
    "Asistencia para niños discapacitados / Assistance for disabled children / 殘疾兒童協助":
      "Assistance for Disabled Children",
  }),
]);

