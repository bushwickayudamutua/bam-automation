const AUTOMATION_CLEAN_RECORD_ENDPOINT = 'https://api.baml.ink/clean-record'
const { address, city, zipCode, apiKey } = input.config()

const clean = async (address, city_state, zip_code) => {
    const params = new URLSearchParams({
        address,
        city_state,
        zip_code,
        apikey: apiKey,
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
const apiResponse = await clean(address, city, zipCode)

output.set(
    'cleaned_address',
    apiResponse?.cleaned_address || [address, city, zipCode].join(' ').trim() || ''
)
output.set('cleaned_address_accuracy',apiResponse?.cleaned_address_accuracy || '')
output.set('bin', apiResponse?.bin || '')
output.set('success', Boolean(apiResponse))
