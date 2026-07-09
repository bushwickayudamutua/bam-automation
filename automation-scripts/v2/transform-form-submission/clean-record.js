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

const passThroughAddress = [address, city, zipCode].join(' ') || ''

const setOutputs = (fields, success) => {
    output.set('phone', fields.phone || '')
    output.set('phone_is_invalid', fields.phone_is_invalid || false)
    output.set('phone_is_intl', fields.phone_is_intl || false)
    output.set('email', fields.email || '')
    output.set('email_error', fields.email_error || '')
    output.set('cleaned_address', fields.cleaned_address || '')
    output.set('cleaned_address_accuracy', fields.cleaned_address_accuracy || '')
    output.set('bin', fields.bin || '')
    output.set('plus_code', fields.plus_code || '')
    output.set('success', success)
}

// clean data; on API failure pass through raw form fields so intake always proceeds
const apiResponse = await clean(email, phone, address, city, zipCode)

if (apiResponse) {
    setOutputs(
        {
            phone: apiResponse.phone || phone,
            phone_is_invalid: apiResponse.phone_is_invalid,
            phone_is_intl: apiResponse.phone_is_intl,
            email: apiResponse.email || email,
            email_error: apiResponse.email_error,
            cleaned_address: apiResponse.cleaned_address || passThroughAddress,
            cleaned_address_accuracy: apiResponse.cleaned_address_accuracy,
            bin: apiResponse.bin,
            plus_code: apiResponse.plus_code,
        },
        true
    )
} else {
    setOutputs(
        {
            phone,
            email,
            cleaned_address: passThroughAddress,
        },
        false
    )
}

