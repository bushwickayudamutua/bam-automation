const AUTOMATION_CLEAN_RECORD_ENDPOINT = 'https://api.baml.ink/clean-record'
const AUTOMATION_APIKEY = '***'
const { email, phone, address, city, zipCode } = input.config()

const clean = async (email, phone, address, city_state, zipcode) => {
    // @ts-ignore
    const params = new URLSearchParams({
        email,
        phone,
        apikey: AUTOMATION_APIKEY,
        dns_check: true,
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

// clean data
const apiResponse = await clean(email, phone, address, city, zipCode)

// default to passing through input data
if (apiResponse) {
    output.set('phone', apiResponse.phone || phone || '')
    output.set('phone_is_invalid', apiResponse.phone_is_invalid || false)
    output.set('phone_is_intl', apiResponse.phone_is_intl || false)
    output.set('email', apiResponse.email || email || '')
    output.set('email_error', apiResponse.email_error || '')
    output.set(
        'cleaned_address',
        apiResponse.cleaned_address || [address, city, zipCode].join(' ') || ''
    )
    output.set('cleaned_address_accuracy', apiResponse.cleaned_address_accuracy || '')
    output.set('bin', apiResponse.bin || '')
    output.set('plus_code', apiResponse.plus_code || '')
    output.set('success', true)
} else {
    output.set('success', false)
}

