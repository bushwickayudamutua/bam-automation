from bam_core.utils.phone import format_phone_number, extract_phone_numbers


def test_format_phone_number():
    valid_us_phone_number = "19294206969"
    assert format_phone_number(valid_us_phone_number) == "(929) 420-6969"
    valid_us_phone_number_without_intl_code = "9294206969"
    assert (
        format_phone_number(valid_us_phone_number_without_intl_code)
        == "(929) 420-6969"
    )
    valid_us_phone_number_with_formatting = "(929) 420-6969"
    assert (
        format_phone_number(valid_us_phone_number_with_formatting)
        == "(929) 420-6969"
    )
    valid_us_phone_number_with_formatting_and_intl_code = "+1 (929) 420-6969"
    assert (
        format_phone_number(
            valid_us_phone_number_with_formatting_and_intl_code
        )
        == "(929) 420-6969"
    )
    invalid_phone_number = "123456"
    assert format_phone_number(invalid_phone_number) is None

    valid_intl_phone_number = "+34666666666"
    assert format_phone_number(valid_intl_phone_number) == "+34 666 66 66 66"


def test_extract_phone_numbers():
    text = "dsilfkhlae (917) 555-5555 jfidalfks(347) 555 5555"
    numbers = extract_phone_numbers(text)
    assert numbers == ["(917) 555-5555", "(347) 555-5555"]
