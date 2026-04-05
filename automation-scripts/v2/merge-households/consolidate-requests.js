const { requestIds, ssRequestIds } = input.config()

async function mergeReqs(tableName, recordIds, mergeFns) {
    // Pull requests from table
    const requestTable = base.getTable(tableName)
    const requestsQuery = await requestTable.selectRecordsAsync({
        recordIds,
        fields: [
            'Type',
            'Request Opened At',
            ...Object.keys(mergeFns),
        ]
    })
    const requests = [...requestsQuery.records]

    // Group requests by type, sorted from oldest to newest
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
            const type = req.getCellValue('Type').id
            if (!requestGroups.has(type)) requestGroups.set(type, [])
            requestGroups.get(type).push(req)
        })

    // Merge fields according to callbacks, delete repeat requests
    for (let [, reqGroup] of requestGroups) {
        const [firstReq, ...rest] = reqGroup

        await requestTable.updateRecordAsync(
            firstReq,
            Object.fromEntries(Object.keys(mergeFns).map((field) => {
                const fn = mergeFns[field]
                const value = fn(reqGroup.map((req) => req.getCellValue(field)))
                return [field, value]
            }))
        )
        await requestTable.deleteRecordsAsync(rest)
    }
}

const mergeNotes = (notes) => notes.filter((note) => note !== '').join('\n')
const getLast = (arr) => arr.pop()

await mergeReqs('Requests', requestIds, {
    'Last Requested': getLast,
    Geocode: getLast,
})
await mergeReqs('Social Service Requests', ssRequestIds, {
    'Last Requested': getLast,
    'Internet Access': (iaLists) =>
        [...new Set(iaLists.map((iaList) => iaList ?? []).flat())],
    'Roof Accessible?': getLast,
    'Street Address': getLast,
    'City, State': getLast,
    'Zip Code': getLast,
    Geocode: getLast,
})

