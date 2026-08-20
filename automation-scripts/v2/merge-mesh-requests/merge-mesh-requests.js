const { requestIds } = input.config()

const meshRequestTable = base.getTable('Mesh Requests')

const requests = (await meshRequestTable.selectRecordsAsync({
    recordIds: requestIds,
    fields: meshRequestTable.fields,
    sorts: [{ field: 'Created At', direction: 'asc' }],
})).records
const [survivor, ...others] = requests
const latest = requests[requests.length - 1]

// Helper to dedupe and extract {id} from linked records or multi-select
const dedupeById = (items) => {
    const seen = new Set()
    const uniqueItems = items
        .flat()
        .filter(Boolean)
        .filter(item => {
            if (seen.has(item.id)) return false
            seen.add(item.id)
            return true
        })
        .map(item => ({ id: item.id }))
    return uniqueItems.length ? uniqueItems : undefined
}

const internetAccess = dedupeById(
    requests.map(r => r.getCellValue('Internet Access'))
)

// Merges text fields — trims each entry, filters blanks, joins with newline
const mergeText = (texts) =>
    texts
        .map(t => t?.trim())
        .filter(Boolean)
        .reverse()
        .join('\n')

const meshHistory = mergeText(requests.map(h => h.getCellValue('MESH History')))

const ADDRESS_ACCURACY_RANK = {
    'Apartment': 3,
    'Building': 2,
    'Address Outside NY': 1,
    'No result': 0,
    '': 0,
    'Invalid Address Provided': -1,
}

const pickAddressReq = () => {
    let bestReq = survivor
    let bestRank = -2
    for (const req of requests) {
        const accuracy = req.getCellValue('Address Accuracy')
        const rank = ADDRESS_ACCURACY_RANK[accuracy?.name ?? ''] ?? -2
        if (rank >= bestRank) {
            bestRank = rank
            bestReq = req
        }
    }

    return bestReq
}

const addrReq = pickAddressReq()

await meshRequestTable.updateRecordAsync(survivor, {
    'Last Requested': latest.getCellValue('Last Requested'),
    'Internet Access': internetAccess,
    'Street Address': addrReq.getCellValue('Street Address'),
    'City, State': addrReq.getCellValue('City, State'),
    'Zip Code': addrReq.getCellValue('Zip Code'),
    Address: addrReq.getCellValue('Address'),
    'Address Accuracy': addrReq.getCellValue('Address Accuracy'),
    'MESH History': meshHistory,
})

for (const record of others) {
    await meshRequestTable.deleteRecordAsync(record)
}
