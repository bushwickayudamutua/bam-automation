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

const ssRequestTable = base.getTable('Social Service Requests')

output.set(
  'ssRequestIds',
  await ssRequestTable.createRecordsAsync(
    ssReqs.map((reqType) => {
      const fields = { Type: { name: reqType } }
      if (reqType === 'Internet de bajo costo en casa / Low-Cost Internet at home / 網絡連結協助') {
        fields['Internet Access'] = internetAccess.map((name) => ({ name }))
        fields['Roof Accessible?'] = roofAccessible
        fields['Address'] = cleanedAddress
        fields['Address Accuracy'] = { name: cleanedAddressAccuracy }
        fields['Building Identification Number'] = Number(bin)
      }
      return { fields }
    })
  )
)
