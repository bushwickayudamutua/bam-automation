const {
  egReqs,
  furnReqs,
  bedReqs,
  kitchenReqs,
  ssReqs,
  internetAccess,
  roofAccessible,
  cleanedAddress,
  cleanedAddressAccuracy,
  bin,
  plusCode,
} = input.config()

const requestTable = base.getTable('Requests')

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
  await requestTable.createRecordsAsync([
    nonFurnItemReqs.map((reqType) => ({ fields: { Type: { name: reqType } } })),
    furnItemReqs.map((reqType) => ({
      fields: { Type: { name: reqType }, Geocode: plusCode || '' },
    })),
  ].flat())
)

let meshRequested = false
for (let i = 0; i < ssReqs.length; i++) {
  if (ssReqs[i] === 'Internet de bajo costo en casa / Low-Cost Internet at home / 網絡連結協助') {
    meshRequested = true
    ssReqs.splice(i, 1)
    break
  }
}

const ssRequestTable = base.getTable('Social Service Requests')

output.set(
  'ssRequestIds',
  await ssRequestTable.createRecordsAsync(
    ssReqs.map((reqType) => ({ fields: { Type: { name: reqType } } }))
  )
)

const meshRequestTable = base.getTable('Mesh Requests')

output.set(
  'meshRequestId',
  await meshRequestTable.createRecordAsync({
    'Internet Access': internetAccess.map((name) => ({ name })),
    Address: cleanedAddress,
    'Address Accuracy': { name: cleanedAddressAccuracy },
    'Building Identification Number': Number(bin),
  })
)
