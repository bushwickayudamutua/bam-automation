const { requestIds, furnRequestIds, ssRequestIds, meshRequestIds } = input.config()

// Retrieve tables
const reqTable = base.getTable('Requests');
const furnReqTable = base.getTable('Furniture Requests');
const ssReqTable = base.getTable('Social Service Requests');
const meshTable = base.getTable('Mesh Requests');
const countTable = base.getTable('Fulfilled Request Count');

async function mergeRequests(table, recordIds, getKey, mergeFns) {
    const requestGroups = new Map()

    const reqs = (await table.selectRecordsAsync({
        recordIds,
        fields: table.fields,
        sorts: [{ field: 'Request Opened At', direction: 'asc' }]
    })).records
    for (const req of reqs) {
        const key = getKey(req)

        if (!requestGroups.has(key)) requestGroups.set(key, [])
        requestGroups.get(key).push(req)
    }

    // Merge fields according to callbacks, delete repeat requests
    for (let [, reqGroup] of requestGroups) {
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

const MESH_STATUS_RANK = {
    'Open': 0,
    'Contacted about Mesh': 1,
    'Interested in Mesh': 2,
    'Needs Panorama': 3,
    'Roof Access In Process': 4,
    'Confirming Permission with Landlord': 5,
    'Roof Access Confirmed': 6,
    'LOS Confirmed': 7,
    'Scheduling IN-PROGRESS': 8,
    'Install Scheduled': 9,
    'Cannot Install': 10,
    'YAY! MESH INSTALLED!': 11,
    'INSTALL PENDING ELDERT REPAIR': 12,
}

const maxMeshStatus = (reqs) => {
    const statuses = reqs.map((req) => req.getCellValue('Status'))
    let bestStatus
    let bestRank = -1
    for (const status of statuses) {
        const rank = MESH_STATUS_RANK[status.name]
        if (rank > bestRank) {
            bestRank = rank
            bestStatus = status
        }
    }

    return bestStatus
}

const ADDRESS_ACCURACY_RANK = {
    'Apartment': 3,
    'Building': 2,
    'Address Outside NY': 1,
    'No result': 0,
    '': 0,
    'Invalid Address Provided': -1,
}

const trimText = (value) => (value ?? '').trim()

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

    if (!(trimText(reqs[bestIdx].getCellValue('Address')) ||
        trimText(reqs[bestIdx].getCellValue('Street Address')))) {
        for (let i = reqs.length - 1; i >= 0; i--) {
            if (trimText(reqs[i].getCellValue('Address'))) return i
        }

        for (let i = reqs.length - 1; i >= 0; i--) {
            if (trimText(reqs[i].getCellValue('Street Address'))) return i
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
        Status: maxMeshStatus,
        'Internet Access': union('Internet Access'),
        'Street Address': fromAddressBundle('Street Address'),
        'City, State': fromAddressBundle('City, State'),
        'Zip Code': fromAddressBundle('Zip Code'),
        Address: (reqs) => {
          const rawAddress = fromAddressBundle('Address')(reqs)
          return trimText(rawAddress)
        },
        'Address Accuracy': fromAddressBundle('Address Accuracy'),
    },
)
