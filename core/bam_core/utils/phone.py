import logging
from typing import List, Optional
import phonenumbers

log = logging.getLogger(__name__)


def is_international_phone_number(phone_number: str) -> bool:
    """
    Check if a phone number is international
    :param phone_number: The phone number to check
    :return: True if the phone number is international AND valid, False otherwise
    """
    try:
        parsed_phone_number = phonenumbers.parse(phone_number, "US")
        # if the phone number is not valid, we can't be sure if it's international or not.
        if not phonenumbers.is_valid_number(parsed_phone_number):
            return False
        return (
            parsed_phone_number.country_code is not None
            and parsed_phone_number.country_code != 1
        )
    except Exception as e:
        log.warning(
            f"Error checking if phone number {phone_number} is international because of {e}"
        )
        return False


def format_phone_number(phone_number: str) -> Optional[str]:
    """
    Format a phone number to the US standard
    :param phone_number: The phone number to format
    :return: The formatted phone number
    """
    try:
        parsed_phone_number = phonenumbers.parse(phone_number, "US")
        if not phonenumbers.is_valid_number(parsed_phone_number):
            return None
        if (
            not parsed_phone_number.country_code
            or parsed_phone_number.country_code == 1
        ):
            return phonenumbers.format_number(
                parsed_phone_number, phonenumbers.PhoneNumberFormat.NATIONAL
            )
        return phonenumbers.format_number(
            parsed_phone_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL
        )

    except Exception as e:
        log.warning(
            f"Error formatting phone number {phone_number} because of {e}"
        )
        return None


def extract_phone_numbers(text: str) -> List[str]:
    """
    Extract and format all phone numbers from an unstructured blob of text.
    This function will only extract **valid** phone numbers, so those with an incorrect area code,
    or the wrong length will be ignored
    :param text: A blob of text.
    :return: A list of formatted phone numbers
    """
    numbers = []
    for match in phonenumbers.PhoneNumberMatcher(text, "US"):
        number = phonenumbers.format_number(
            match.number, phonenumbers.PhoneNumberFormat.NATIONAL
        )
        numbers.append(number)
    return numbers
