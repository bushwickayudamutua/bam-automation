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

const NO_EMAIL_ERROR = 'No email address provided'
const NO_ADDRESS_ACCURACY = 'No result'

const passThroughFields = {
    phone: phone || '',
    phone_is_invalid: !(phone || '').trim(),
    phone_is_intl: false,
    email: email || '',
    email_error: (email || '').trim() ? '' : NO_EMAIL_ERROR,
    cleaned_address: passThroughAddress,
    cleaned_address_accuracy: passThroughAddress.trim() ? '' : NO_ADDRESS_ACCURACY,
    bin: '',
    plus_code: '',
}

const stringOrPassThrough = (value, fallback) =>
    value === null || value === undefined || value === '' ? fallback : value

const setOutputs = (fields, success) => {
    const resolvedPhone = stringOrPassThrough(fields.phone, passThroughFields.phone)
    let phoneIsInvalid = fields.phone_is_invalid ?? passThroughFields.phone_is_invalid
    if (!resolvedPhone.trim()) {
        phoneIsInvalid = true
    }

    output.set('phone', resolvedPhone)
    output.set('phone_is_invalid', phoneIsInvalid)
    output.set('phone_is_intl', fields.phone_is_intl ?? passThroughFields.phone_is_intl)

    const resolvedEmail = stringOrPassThrough(fields.email, passThroughFields.email)
    let emailError = stringOrPassThrough(fields.email_error, passThroughFields.email_error)
    if (!resolvedEmail.trim()) {
        emailError = NO_EMAIL_ERROR
    }

    output.set('email', resolvedEmail)
    output.set('email_error', emailError)

    const resolvedCleanedAddress = stringOrPassThrough(
        fields.cleaned_address,
        passThroughFields.cleaned_address
    )
    let cleanedAddressAccuracy = stringOrPassThrough(
        fields.cleaned_address_accuracy,
        passThroughFields.cleaned_address_accuracy
    )
    if (!resolvedCleanedAddress.trim()) {
        cleanedAddressAccuracy = NO_ADDRESS_ACCURACY
    }

    output.set('cleaned_address', resolvedCleanedAddress)
    output.set('cleaned_address_accuracy', cleanedAddressAccuracy)
    output.set('bin', stringOrPassThrough(fields.bin, passThroughFields.bin))
    output.set('plus_code', stringOrPassThrough(fields.plus_code, passThroughFields.plus_code))
    output.set('success', success)
}

// clean data; on API failure pass through raw form fields so intake always proceeds
const apiResponse = await clean(email, phone, address, city, zipCode)

if (apiResponse) {
    setOutputs(
        {
            phone: apiResponse.phone,
            phone_is_invalid: apiResponse.phone_is_invalid,
            phone_is_intl: apiResponse.phone_is_intl,
            email: apiResponse.email,
            email_error: apiResponse.email_error,
            cleaned_address: apiResponse.cleaned_address,
            cleaned_address_accuracy: apiResponse.cleaned_address_accuracy,
            bin: apiResponse.bin,
            plus_code: apiResponse.plus_code,
        },
        true
    )
} else {
    setOutputs(passThroughFields, false)
}

