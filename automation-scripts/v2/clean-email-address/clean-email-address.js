const AUTOMATION_CLEAN_RECORD_ENDPOINT = 'https://api.baml.ink/clean-record'
const { email, apiKey } = input.config()

const clean = async (email) => {
    const params = new URLSearchParams({
      email,
      dns_check: true.toString(),
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
const apiResponse = await clean(email)

output.set('email', apiResponse?.email || email || '')
output.set('email_error', apiResponse?.email_error || '')
output.set('success', Boolean(apiResponse))
