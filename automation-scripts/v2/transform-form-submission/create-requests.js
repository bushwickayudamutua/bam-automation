const {
  egReqs,
  furnReqs,
  bedReqs,
  kitchenReqs,
  ssReqs,
  internetAccess,
  cleanedAddress,
  cleanedAddressAccuracy,
  bin,
  plusCode,
  formSubmittedAt,
} = input.config()

// Retrieve tables
const requestTable = base.getTable('Requests')
const furnRequestTable = base.getTable('Furniture Requests')
const ssRequestTable = base.getTable('Social Service Requests')
const meshRequestTable = base.getTable('Mesh Requests')

// 'Last Requested' is a date field; normalize the submission timestamp to the
// local (NY) day so late-evening submissions don't land on the next UTC day
function submissionDay(value) {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  try {
    return date.toLocaleDateString('en-CA', { timeZone: 'America/New_York' })
  } catch (error) {
    return date.toISOString().slice(0, 10)
  }
}

const lastRequested = submissionDay(formSubmittedAt)
const lastRequestedFields = lastRequested ? { 'Last Requested': lastRequested } : {}

const nonFurnItemReqs = [
  egReqs.filter((egType) =>
    !['Muebles / Furniture / 家具', 'Cosas de Cocina / Kitchen Supplies / 廚房用品'].includes(egType)
  ),
  kitchenReqs,
].flat()

const furnItemReqs = [
  furnReqs.filter((furnType) => furnType !== 'Cama / Bed / 床'),
  bedReqs,
].flat()

output.set(
  'requestIds',
  await requestTable.createRecordsAsync(
    nonFurnItemReqs.map((reqType) => ({
      fields: { Type: { name: reqType }, ...lastRequestedFields },
    }))
  )
)

output.set(
  'furnRequestIds',
  await furnRequestTable.createRecordsAsync(
    furnItemReqs.map((reqType) => ({
      fields: {
        Type: { name: reqType },
        Geocode: plusCode || '',
        ...lastRequestedFields,
      },
    }))
  )
)

let meshRequested = false
for (let i = 0; i < ssReqs.length; i++) {
  if (ssReqs[i] === 'Internet de bajo costo en casa / Low-Cost Internet at home / 網絡連結協助') {
    meshRequested = true
    ssReqs.splice(i, 1)
    break
  }
}

output.set(
  'ssRequestIds',
  await ssRequestTable.createRecordsAsync(
    ssReqs.map((reqType) => ({
      fields: { Type: { name: reqType }, ...lastRequestedFields },
    }))
  )
)

if (meshRequested) {
  const binNumber = bin ? Number(bin) : NaN
  const meshFields = {
    // Single selects have no default on API-created records; without this,
    // consolidate-requests' maxMeshStatus would see a null Status
    Status: { name: 'Open' },
    'Internet Access': (internetAccess || []).map((name) => ({ name })),
    Address: cleanedAddress,
    // '' can't match a select option; 'No result' mirrors clean-record's
    // no-address sentinel for the API-failure passthrough path
    'Address Accuracy': { name: cleanedAddressAccuracy || 'No result' },
    ...lastRequestedFields,
  }
  if (Number.isFinite(binNumber)) {
    meshFields['Building Identification Number'] = binNumber
  }
  output.set('meshRequestId', await meshRequestTable.createRecordAsync(meshFields))
} else {
  output.set('meshRequestId', null)
}
