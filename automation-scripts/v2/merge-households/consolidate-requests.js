const { requestIds, furnRequestIds, ssRequestIds, meshRequestIds } = input.config()

// Retrieve tables
const reqTable = base.getTable('Requests');
const furnReqTable = base.getTable('Furniture Requests');
const ssReqTable = base.getTable('Social Service Requests');
const meshTable = base.getTable('Mesh Requests');

async function mergeRequests(table, reqIds, getKey, mergeFns) {
    if (!reqIds.length) return

    // Step 1: group requests by key, sorted from oldest to newest
    const requestGroups = new Map()

    const reqs = (await table.selectRecordsAsync({
        recordIds: reqIds,
        fields: table.fields,
        sorts: [{ field: 'Request Opened At', direction: 'asc' }]
    })).records
    for (const req of reqs) {
        const key = getKey(req)

        if (!requestGroups.has(key)) requestGroups.set(key, [])
        requestGroups.get(key).push(req)
    }

    // Step 2: merge fields according to callbacks, delete repeat requests
    for (const [, reqGroup] of requestGroups) {
        const [firstReq, ...rest] = reqGroup

        const mergedFields = {}
        for (const [field, fn] of Object.entries(mergeFns)) {
            mergedFields[field] = fn(reqGroup)
        }
        await table.updateRecordAsync(firstReq, mergedFields)
        await table.deleteRecordsAsync(rest)
    }
}

const getLast = (field) => (arr) => arr[arr.length - 1].getCellValue(field)
const union = (field) => (reqs) => {
    const lists = reqs.map((req) => req.getCellValue(field))
    const allSelectionIds = lists.map((list) => list ?? []).flat().map(({ id }) => id)
    const uniqIds = [...new Set(allSelectionIds)]
    return uniqIds.map((id) => ({ id }))
}
const mergeText = (texts) =>
    texts
        .map(t => t?.trim())
        .filter(Boolean)
        .reverse()
        .join('\n')

const ADDRESS_ACCURACY_RANK = {
    'Apartment': 3,
    'Building': 2,
    'Address Outside NY': 1,
    'No result': 0,
    '': 0,
    'Invalid Address Provided': -1,
}

const pickAddressBundleIndex = (reqs) => {
    let bestIdx = 0
    let bestRank = -2
    for (let i = 0; i < reqs.length; i++) {
        const accuracy = reqs[i].getCellValue('Address Accuracy')
        const rank = ADDRESS_ACCURACY_RANK[accuracy?.name ?? ''] ?? -2
        if (rank >= bestRank) {
            bestRank = rank
            bestIdx = i
        }
    }

    return bestIdx
}

const fromAddressBundle = (field) => (reqs) => {
    const idx = pickAddressBundleIndex(reqs)
    return reqs[idx].getCellValue(field)
}

function getType(req) {
    return req.getCellValue('Type').id
}

await mergeRequests(reqTable, requestIds, getType, {
    'Last Requested': getLast('Last Requested'),
})
await mergeRequests(furnReqTable, furnRequestIds, getType, {
    'Last Requested': getLast('Last Requested'),
    Geocode: getLast('Geocode'),
})
await mergeRequests(ssReqTable, ssRequestIds, getType, {
    'Last Requested': getLast('Last Requested'),
    'Partner Org': union('Partner Org'),
})
await mergeRequests(
    meshTable,
    meshRequestIds,
    (req) => req.getCellValue('Building Identification Number'),
    {
        'Last Requested': getLast('Last Requested'),
        'MESH History': (reqs) =>
            mergeText(reqs.map(r => r.getCellValue('MESH History')))
        'Internet Access': union('Internet Access'),
        'Street Address': fromAddressBundle('Street Address'),
        'City, State': fromAddressBundle('City, State'),
        'Zip Code': fromAddressBundle('Zip Code'),
        Address: fromAddressBundle('Address'),
        'Address Accuracy': fromAddressBundle('Address Accuracy'),
    },
)
