const {
  egReqs,
  furnReqs,
  bedReqs,
  kitchenReqs,
  ssReqs,
  streetAddress,
  cityState,
  zipCode,
  internetAccess,
  formSubmittedAt,
  isClean,
  address,
  addressAccuracy,
  bin,
  plusCode,
} = input.config()

// Retrieve tables
const requestTable = base.getTable('Requests')
const furnRequestTable = base.getTable('Furniture Requests')
const ssRequestTable = base.getTable('Social Service Requests')
const meshRequestTable = base.getTable('Mesh Requests')

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
      fields: { Type: { name: reqType }, 'Last Requested': formSubmittedAt },
    }))
  )
)

output.set(
  'furnRequestIds',
  await furnRequestTable.createRecordsAsync(
    furnItemReqs.map((reqType) => ({
      fields: {
        Type: { name: reqType },
        Geocode: plusCode,
        'Last Requested': formSubmittedAt,
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
      fields: { Type: { name: reqType }, 'Last Requested': formSubmittedAt },
    }))
  )
)

if (meshRequested) {
  output.set(
    'meshRequestId',
    await meshRequestTable.createRecordAsync({
      'Building Identification Number': isClean ? Number(bin) : undefined,
      'Internet Access': internetAccess.map((name) => ({ name })),
      'Street Address': streetAddress,
      'City, State': cityState,
      'Zip Code': zipCode,
      Address: address,
      'Address Accuracy': isClean ? { name: addressAccuracy } : undefined,
      'Last Requested': formSubmittedAt,
    })
  )
} else {
  output.set('meshRequestId', null)
}
