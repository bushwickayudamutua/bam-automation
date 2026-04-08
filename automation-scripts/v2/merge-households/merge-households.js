const { newHouseholdId, oldHouseholdIds } = input.config()
const [ survivorId, ...otherOldIds ] = oldHouseholdIds

const householdTable = base.getTable('Households')
const getHousehold = async (householdId) => {
    const household = await householdTable.selectRecordAsync(householdId)
    if (household === null) throw `Household ${householdId} does not exist`
    return household
}

const newHousehold = await getHousehold(newHouseholdId)
const survivor = await getHousehold(survivorId)
const otherOldHouseholds = await Promise.all(otherOldIds.map(getHousehold))

const allHouseholds = [survivor, ...otherOldHouseholds, newHousehold]

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
    allHouseholds.map(h => h.getCellValue('Languages'))
)

const requests = dedupeById(
    allHouseholds.map(h => h.getCellValue('Requests'))
)

const socialServiceRequests = dedupeById(
    allHouseholds.map(h => h.getCellValue('Social Service Requests'))
)

// Merges text fields without deduping — trims each entry, filters blanks, joins with newline
const mergeText = (texts) =>
    texts
        .map(t => t?.trim())
        .filter(Boolean)
        .join('\n')

// Merges text fields with deduping — trim happens before filter so empty-after-trim strings are dropped cleanly
const mergeTextDeduped = (texts) => {
    const seen = new Set()
    return texts
        .map(t => t?.trim())
        .filter(Boolean)
        .filter(text => {
            if (seen.has(text)) return false
            seen.add(text)
            return true
        })
        .join('\n')
}

const otherLanguages = mergeTextDeduped(
    [...allHouseholds]
        .reverse()
        .map(h => h.getCellValue('Other Languages'))
)

const notes = mergeText(
    [...allHouseholds]
        .reverse()
        .map(h => h.getCellValue('Notes'))
)

await householdTable.updateRecordAsync(survivor, {
    Name: newHousehold.getCellValue('Name'),
    "Int'l Phone Number?": newHousehold.getCellValue("Int'l Phone Number?"),
    'Invalid Phone Number?': newHousehold.getCellValue("Invalid Phone Number?"),
    Email: newHousehold.getCellValue('Email'),
    'Email Error': newHousehold.getCellValue('Email Error'),
    Languages: languages,
    "Other Languages": otherLanguages,
    Notes: notes,
    Requests: requests,
    'Social Service Requests': socialServiceRequests,
    'Needs Delivery': allHouseholds.some(h => h.getCellValue('Needs Delivery')) || null,
    'Needs Email Outreach': allHouseholds.some(h => h.getCellValue('Needs Email Outreach')) || null,
})

const recordsToDelete = [newHousehold, ...otherOldHouseholds]
for (const record of recordsToDelete) {
    await householdTable.deleteRecordAsync(record)
}
