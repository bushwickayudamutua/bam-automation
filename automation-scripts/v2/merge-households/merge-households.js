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

const minDate = (dates) => {
    const valid = dates.filter(Boolean)
    if (!valid.length) return undefined
    return valid.reduce((min, d) => (d < min ? d : min))
}

const maxDate = (dates) => {
    const valid = dates.filter(Boolean)
    if (!valid.length) return undefined
    return valid.reduce((max, d) => (d > max ? d : max))
}

const legacyFirstDate = minDate(
    allHouseholds.map(h => h.getCellValue('Legacy First Date Submitted'))
)
const legacyLastDate = maxDate(
    allHouseholds.map(h => h.getCellValue('Legacy Last Date Submitted'))
)
const lastTexted = maxDate(allHouseholds.map(h => h.getCellValue('Last Texted')))
const lastCalled = maxDate(allHouseholds.map(h => h.getCellValue('Last Called')))

const pickAppointmentFields = (households) => {
    const maxApptDate = maxDate(households.map(h => h.getCellValue('Appointment Date')))
    if (!maxApptDate) return {}
    let source = null
    for (let i = households.length - 1; i >= 0; i--) {
        const d = households[i].getCellValue('Appointment Date')
        if (d && d.getTime() === maxApptDate.getTime()) {
            source = households[i]
            break
        }
    }
    return {
        'Appointment Date': maxApptDate,
        'Appointment Time': source.getCellValue('Appointment Time'),
        'Appointment Status': source.getCellValue('Appointment Status'),
    }
}
const appointmentFields = pickAppointmentFields(allHouseholds)

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

const meshRequests = dedupeById(
    allHouseholds.map(h => h.getCellValue('Mesh Requests'))
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
    'Mesh Requests': meshRequests,
    'Needs Delivery': allHouseholds.some(h => h.getCellValue('Needs Delivery')),
    'Needs Email Outreach': allHouseholds.some(h => h.getCellValue('Needs Email Outreach')),
    ...(legacyFirstDate != null && { 'Legacy First Date Submitted': legacyFirstDate }),
    ...(legacyLastDate != null && { 'Legacy Last Date Submitted': legacyLastDate }),
    ...(lastTexted != null && { 'Last Texted': lastTexted }),
    ...(lastCalled != null && { 'Last Called': lastCalled }),
    ...appointmentFields,
})

const recordsToDelete = [newHousehold, ...otherOldHouseholds]
for (const record of recordsToDelete) {
    await householdTable.deleteRecordAsync(record)
}
