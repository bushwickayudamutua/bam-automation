const AUTOMATION_CLEAN_RECORD_ENDPOINT = 'https://api.baml.ink/clean-record'
const { email, phone, address, city, zipCode, apiKey } = input.config()

const clean = async (email, phone, address, city_state, zip_code) => {
    const params = new URLSearchParams({
        email,
        phone,
        apikey: apiKey,
        dns_check: true.toString(),
        address,
        city_state,
        zip_code,
    })
    const url = `${AUTOMATION_CLEAN_RECORD_ENDPOINT}?${params}`
    try {
      const response = await fetch(url)
      if (response.ok) {
        return await response.json()
      }
      const body = await response.text()
      console.log(`API request failed with status: ${response.status} and response:\n${body}`)
    } catch(error) {
      console.log(`Unexpected error: ${error}`)
    }
}

// clean data; on API failure pass through raw form fields so intake always proceeds
const apiResponse = await clean(email, phone, address, city, zipCode)

output.set('phone', apiResponse?.phone || phone || '')
output.set('phone_is_invalid', apiResponse?.phone_is_invalid || false)
output.set('phone_is_intl', apiResponse?.phone_is_intl || false)
output.set('email', apiResponse?.email || email || '')
output.set('email_error', apiResponse?.email_error || '')
output.set(
    'cleaned_address',
    apiResponse?.cleaned_address || [address, city, zipCode].join(' ') || ''
)
output.set('cleaned_address_accuracy',apiResponse?.cleaned_address_accuracy || '')
output.set('bin', apiResponse?.bin || '')
output.set('plus_code', apiResponse?.plus_code || '')
output.set('success', Boolean(apiResponse))
