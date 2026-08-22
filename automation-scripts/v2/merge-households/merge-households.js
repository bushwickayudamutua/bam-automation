const { householdIds } = input.config()

const householdTable = base.getTable('Households')

const households = (await householdTable.selectRecordsAsync({
    recordIds: householdIds,
    fields: householdTable.fields,
    sorts: [{ field: 'Created At', direction: 'asc' }],
})).records
const [survivor, ...others] = households
const latest = households[households.length - 1]

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

const languages = dedupeById(
    households.map(h => h.getCellValue('Languages'))
)

const requests = dedupeById(
    households.map(h => h.getCellValue('Requests'))
)

const furnitureRequests = dedupeById(
    households.map(h => h.getCellValue('Furniture Requests'))
)

const socialServiceRequests = dedupeById(
    households.map(h => h.getCellValue('Social Service Requests'))
)

const meshRequests = dedupeById(
    households.map(h => h.getCellValue('Mesh Requests'))
)

// Merges text fields without deduping — trims each entry, filters blanks, joins with newline
const mergeText = (texts) =>
    texts
        .map(t => t?.trim())
        .filter(Boolean)
        .reverse()
        .join('\n')

// Merges text fields with deduping — trim happens before filter so empty-after-trim strings are dropped cleanly
const mergeTextDeduped = (texts) => {
    const seen = new Set()
    return texts
        .map(t => t?.trim())
        .filter(Boolean)
        .reverse()
        .filter(text => {
            if (seen.has(text)) return false
            seen.add(text)
            return true
        })
        .join('\n')
}

const notes = mergeText(households.map(h => h.getCellValue('Notes')))

const otherLanguages = mergeTextDeduped(
    households.map(h => h.getCellValue('Other Languages'))
)

await householdTable.updateRecordAsync(survivor, {
    Name: latest.getCellValue('Name'),
    "Int'l Phone Number?": latest.getCellValue("Int'l Phone Number?"),
    'Invalid Phone Number?': latest.getCellValue("Invalid Phone Number?"),
    Email: latest.getCellValue('Email'),
    'Email Error': latest.getCellValue('Email Error'),
    Languages: languages,
    "Other Languages": otherLanguages,
    Notes: notes,
    Requests: requests,
    'Furniture Requests': furnitureRequests,
    'Social Service Requests': socialServiceRequests,
    'Mesh Requests': meshRequests,
    'Needs Delivery': households.some(h => h.getCellValue('Needs Delivery')),
    'Needs Email Outreach': households.some(h => h.getCellValue('Needs Email Outreach')),
})

for (const record of others) {
    await householdTable.deleteRecordAsync(record)
}

output.set('householdId', survivor.id)
