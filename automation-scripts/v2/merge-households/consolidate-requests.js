const { requestIds, furnRequestIds, ssRequestIds, meshRequestIds } = input.config()

async function mergeReqs(tableName, recordIds, keyField, mergeFns) {
    if (!recordIds?.length) return

    // Pull requests from table
    const requestTable = base.getTable(tableName)
    const requestsQuery = await requestTable.selectRecordsAsync({
        recordIds,
        fields: [
            keyField,
            'Request Opened At',
            ...Object.keys(mergeFns),
        ]
    })
    const requests = [...requestsQuery.records]

    // Group requests by key, sorted from oldest to newest
    const requestGroups = new Map()

    requests
        .sort((r1, r2) => {
            const r1OpenedAt = r1.getCellValue('Request Opened At')
            const r2OpenedAt = r2.getCellValue('Request Opened At')
            if (r1OpenedAt < r2OpenedAt) return -1
            if (r1OpenedAt > r2OpenedAt) return 1
            return 0
        })
        .forEach((req) => {
            const rawKey = req.getCellValue(keyField)
            let key = (rawKey !== null && typeof rawKey === 'object')
                ? rawKey.id
                : rawKey
            // A missing/blank key (e.g. a Mesh Request with no Building
            // Identification Number) does not mean these records are the same
            // household. Give each unkeyed record a unique key so it stays in
            // its own group and is never merged with unrelated records.
            if (key == null || key === '') key = Symbol('unkeyed')
            if (!requestGroups.has(key)) requestGroups.set(key, [])
            requestGroups.get(key).push(req)
        })

    // Survivor = earliest Request Opened At
    for (let [, reqGroup] of requestGroups) {
        const [firstReq, ...rest] = reqGroup

        const mergedFields = Object.fromEntries(
            Object.keys(mergeFns)
                .map((field) => {
                    const fn = mergeFns[field]
                    const value = fn(
                        reqGroup.map((req) => req.getCellValue(field)),
                        reqGroup,
                    )
                    return [field, value]
                })
                .filter(([, value]) => value != null && !(Array.isArray(value) && value.length === 0))
        )
        if (Object.keys(mergedFields).length) {
            await requestTable.updateRecordAsync(firstReq, mergedFields)
        }
        await requestTable.deleteRecordsAsync(rest)
    }
}

const minDate = (dates) => {
    const valid = dates.filter(Boolean)
    if (!valid.length) return undefined
    return valid.reduce((min, d) => (d < min ? d : min))
}
const getLast = (arr) => arr[arr.length - 1]
const trimText = (value) => (value || '').trim()

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

const ADDRESS_ACCURACY_RANK = {
    'Apartment': 3,
    'Building': 2,
    'Address Outside NY': 1,
    'No result': 0,
    '': 0,
    'Invalid Address Provided': -1,
}

const maxMeshStatus = (statuses) => {
    let best = null
    let bestRank = -1
    for (const status of statuses) {
        if (!status) continue
        const rank = MESH_STATUS_RANK[status.name] ?? -1
        if (rank > bestRank) {
            bestRank = rank
            best = status
        }
    }
    return best ? { id: best.id } : null
}

const pickAddressBundleIndex = (reqGroup) => {
    let bestIdx = 0
    let bestRank = -2
    for (let i = 0; i < reqGroup.length; i++) {
        const accuracy = reqGroup[i].getCellValue('Address Accuracy')
        const rank = ADDRESS_ACCURACY_RANK[accuracy?.name ?? ''] ?? -2
        if (rank > bestRank || (rank === bestRank && i > bestIdx)) {
            bestRank = rank
            bestIdx = i
        }
    }

    const hasAddressText = (idx) =>
        trimText(reqGroup[idx].getCellValue('Address')) ||
        trimText(reqGroup[idx].getCellValue('Street Address'))

    if (!hasAddressText(bestIdx)) {
        for (let i = reqGroup.length - 1; i >= 0; i--) {
            if (trimText(reqGroup[i].getCellValue('Address'))) {
                bestIdx = i
                break
            }
        }
        if (!trimText(reqGroup[bestIdx].getCellValue('Address'))) {
            for (let i = reqGroup.length - 1; i >= 0; i--) {
                if (trimText(reqGroup[i].getCellValue('Street Address'))) {
                    bestIdx = i
                    break
                }
            }
        }
    }

    return bestIdx
}

let addressBundleCache = { group: null, idx: 0 }
const addressBundleIndex = (reqGroup) => {
    if (reqGroup !== addressBundleCache.group) {
        addressBundleCache.group = reqGroup
        addressBundleCache.idx = pickAddressBundleIndex(reqGroup)
    }
    return addressBundleCache.idx
}

const fromAddressBundle = (field) => (_, reqGroup) => {
    const idx = addressBundleIndex(reqGroup)
    if (field === 'Address') {
        let address = trimText(reqGroup[idx].getCellValue('Address'))
        return address || null
    }
    const value = reqGroup[idx].getCellValue(field)
    if (field === 'Address Accuracy') {
        return value ? { id: value.id } : null
    }
    return value
}

await mergeReqs('Requests', requestIds, 'Type', {
    'Last Requested': getLast,
    'Legacy Date Submitted': minDate,
})
await mergeReqs('Furniture Requests', furnRequestIds, 'Type', {
    'Last Requested': getLast,
    Geocode: getLast,
    'Legacy Date Submitted': minDate,
})
await mergeReqs('Social Service Requests', ssRequestIds, 'Type', {
    'Last Requested': getLast,
    'Legacy Date Submitted': minDate,
    'Partner Org': (orgLists) => {
        const allSelectionIds = orgLists.map((orgList) => orgList ?? []).flat().map(({ id }) => id)
        const uniqIds = [...new Set(allSelectionIds)]
        return uniqIds.map((id) => ({ id }))
    },
})
await mergeReqs('Mesh Requests', meshRequestIds, 'Building Identification Number', {
    'Last Requested': getLast,
    'Legacy Date Submitted': minDate,
    Status: maxMeshStatus,
    'Internet Access': (iaLists) => {
        const allSelectionIds = iaLists.map((iaList) => iaList ?? []).flat().map(({ id }) => id)
        const uniqIds = [...new Set(allSelectionIds)]
        return uniqIds.map((id) => ({ id }))
    },
    'Street Address': fromAddressBundle('Street Address'),
    'City, State': fromAddressBundle('City, State'),
    'Zip Code': fromAddressBundle('Zip Code'),
    Address: fromAddressBundle('Address'),
    'Address Accuracy': fromAddressBundle('Address Accuracy'),
})
