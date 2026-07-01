const { requestIds, ssRequestIds, meshRequestIds } = input.config()

async function mergeReqs(tableName, recordIds, keyField, mergeFns) {
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
            const key = typeof rawKey === 'object'
                ? rawKey.id
                : rawKey
            if (!requestGroups.has(key)) requestGroups.set(key, [])
            requestGroups.get(key).push(req)
        })

    // Merge fields according to callbacks, delete repeat requests
    for (let [, reqGroup] of requestGroups) {
        const [firstReq, ...rest] = reqGroup

        const mergedFields = Object.fromEntries(Object.keys(mergeFns).map((field) => {
            const fn = mergeFns[field]
            const value = fn(reqGroup.map((req) => req.getCellValue(field)))
            return [field, value]
        }))
        await requestTable.updateRecordAsync(
            firstReq, mergedFields
        )
        await requestTable.deleteRecordsAsync(rest)
    }
}

const minDate = (dates) => {
    const valid = dates.filter(Boolean)
    if (!valid.length) return undefined
    return valid.reduce((min, d) => (d < min ? d : min))
}
const getLast = (arr) => arr.pop()

await mergeReqs('Requests', requestIds, 'Type', {
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
    'Internet Access': (iaLists) => {
        const allSelectionIds = iaLists.map((iaList) => iaList ?? []).flat().map(({ id }) => id)
        const uniqIds = [...new Set(allSelectionIds)]
        return uniqIds.map((id) => ({ id }))
    },
    'Street Address': getLast,
    'City, State': getLast,
    'Zip Code': getLast,
    Address: getLast,
    'Address Accuracy': getLast,
})
