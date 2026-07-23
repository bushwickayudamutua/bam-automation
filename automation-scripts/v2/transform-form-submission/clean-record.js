const AUTOMATION_CLEAN_RECORD_ENDPOINT = 'https://api.baml.ink/clean-record'
const { email, phone, address, city, zipCode, apiKey } = input.config()

const clean = async (email, phone, address, city_state, zipcode) => {
    const params = new URLSearchParams({
        email,
        phone,
        apikey: apiKey,
        dns_check: true.toString(),
        address,
        city_state,
        zipcode,
    })
    const url = `${AUTOMATION_CLEAN_RECORD_ENDPOINT}?${params}`
    const response = await fetch(url)
    const data = await response.json()
    if (response.status === 200) {
        return data
    } else {
        console.log(`API request failed with status: ${response.status} and response:\n${JSON.stringify(data)}`)
        return undefined
    }
}

const NO_EMAIL_ERROR = 'No email address provided'
const NO_ADDRESS_ACCURACY = 'No result'

// clean data; on API failure pass through raw form fields so intake always proceeds
const apiResponse = await clean(email, phone, address, city, zipCode)

const cleanedPhone = apiResponse?.phone || phone || ''
output.set('phone', cleanedPhone)
output.set('phone_is_invalid', cleanedPhone.trim()
    ? apiResponse?.phone_is_invalid || false
    : true
)
output.set('phone_is_intl', apiResponse?.phone_is_intl || false)

const cleanedEmail = apiResponse?.email || email || ''
output.set('email', cleanedEmail)
output.set('email_error', cleanedEmail.trim()
    ? apiResponse?.email_error || ''
    : NO_EMAIL_ERROR
)

const cleanedAddress = apiResponse?.cleaned_address || [address, city, zipCode].join(' ') || ''
output.set('cleaned_address', cleanedAddress)
output.set('cleaned_address_accuracy', cleanedAddress.trim()
    ? apiResponse?.cleaned_address_accuracy || ''
    : NO_ADDRESS_ACCURACY
)
output.set('bin', apiResponse?.bin || '')
output.set('plus_code', apiResponse?.plus_code || '')
output.set('success', Boolean(apiResponse)
