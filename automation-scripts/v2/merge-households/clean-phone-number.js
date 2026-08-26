const AUTOMATION_CLEAN_RECORD_ENDPOINT = 'https://api.baml.ink/clean-record'
const { phone, apiKey } = input.config()

const clean = async (phone) => {
    const params = new URLSearchParams({ phone, apikey: apiKey })
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
const apiResponse = await clean(phone)

output.set('phone', apiResponse?.phone || phone || '')
output.set('phone_is_invalid', apiResponse?.phone_is_invalid || false)
output.set('phone_is_intl', apiResponse?.phone_is_intl || false)
output.set('success', Boolean(apiResponse))
