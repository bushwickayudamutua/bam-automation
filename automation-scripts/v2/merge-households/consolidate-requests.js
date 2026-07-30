const { requestIds, furnRequestIds, ssRequestIds, meshRequestIds } = input.config()

// Retrieve tables
const reqTable = base.getTable('Requests');
const furnReqTable = base.getTable('Furniture Requests');
const ssReqTable = base.getTable('Social Service Requests');
const meshTable = base.getTable('Mesh Requests');

async function mergeRequests(table, reqIds, getKey, mergeFns) {
    if (!reqIds?.length) return

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

        // Skip null/empty merge results so a sparse duplicate can't clear
        // populated fields on the survivor
        const mergedFields = {}
        for (const [field, fn] of Object.entries(mergeFns)) {
            const value = fn(reqGroup)
            if (value == null || value === '' ||
                (Array.isArray(value) && !value.length)) continue
            mergedFields[field] = value
        }
        if (Object.keys(mergedFields).length) {
            await table.updateRecordAsync(firstReq, mergedFields)
        }
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
const anyChecked = (field) => (reqs) =>
    reqs.some((req) => req.getCellValue(field)) || null

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

const unknownMeshStatuses = new Set()

const maxMeshStatus = (reqs) => {
    let bestStatus = null
    let bestRank = -1
    for (const req of reqs) {
        const status = req.getCellValue('Status')
        if (!status) continue
        const rank = MESH_STATUS_RANK[status.name]
        if (rank === undefined) {
            unknownMeshStatuses.add(status.name)
            continue
        }
        if (rank > bestRank) {
            bestRank = rank
            bestStatus = status
        }
    }

    // null (not undefined) so an unrankable group leaves the survivor's
    // Status untouched via the null-skip in mergeRequests
    return bestStatus ? { id: bestStatus.id } : null
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
        // Unknown accuracy names rank like 'No result', not below 'Invalid'
        const rank = ADDRESS_ACCURACY_RANK[accuracy?.name ?? ''] ?? 0
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
        'Roof Accessible?': anyChecked('Roof Accessible?'),
        'Has LOS?': anyChecked('Has LOS?'),
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

// Surface status names missing from MESH_STATUS_RANK so map drift is visible
output.set('unknownMeshStatuses', [...unknownMeshStatuses])
