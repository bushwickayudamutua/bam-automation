from typing import List, TYPE_CHECKING
from datetime import date

from pyairtable.orm import Model, fields as F

from bam_core import settings


def build_meta(table_name: str):
    return {
        'base_id': settings.AIRTABLE_V2_BASE_ID,
        'api_key': settings.AIRTABLE_V2_TOKEN,
        'table_name': table_name,
    }


class FormSubmission(Model):
    bam_id = F.AutoNumberField('ID')

    # household details
    name = F.TextField('Name')
    phone_number = F.PhoneNumberField('Phone Number')
    email = F.EmailField('Email')
    languages = F.MultipleSelectField('Languages')
    notes = F.TextField('Notes')

    # address details
    street_address = F.TextField('Street Address')
    city_and_state = F.TextField('City, State')
    zip_code = F.NumberField('Zip Code')

    # essential goods requests
    request_types = F.MultipleSelectField('Request Types')

    furniture_acknowledgement = F.CheckboxField('Furniture Acknowledgement')
    furniture_items = F.MultipleSelectField('Furniture Items')
    bed_details = F.MultipleSelectField('Bed Details')

    kitchen_items = F.MultipleSelectField('Kitchen Items')

    # social service requests
    ss_request_types = F.MultipleSelectField('Social Service Requests')

    internet_access = F.MultipleSelectField('Internet Access')
    roof_is_accessible = F.CheckboxField('Roof Accessible?')

    # timeline metadata
    legacy_first_date_submitted = F.DateField('Legacy First Date Submitted')
    legacy_last_date_submitted = F.DateField('Legacy Last Date Submitted')

    Meta = build_meta('Assistance Request Form Submissions')

    if TYPE_CHECKING:
        def __init__(self, *, name: str, phone_number: str, email: str,
                     languages: List[str], notes: str, street_address: str,
                     city_and_state: str, zip_code: int,
                     request_types: List[str], furniture_acknowledgement: bool,
                     furniture_items: List[str], bed_details: List[str],
                     kitchen_items: List[str], ss_request_types: List[str],
                     internet_access: List[str], roof_is_accessible: bool,
                     legacy_first_date_submitted: date,
                     legacy_last_date_submitted: date,): ...


class Household(Model):
    bam_id = F.AutoNumberField('ID')
    name = F.TextField('Name')

    phone_number = F.PhoneNumberField('Phone Number')
    phone_is_invalid = F.CheckboxField('Invalid Phone Number?')
    phone_is_intl = F.CheckboxField("Int'l Phone Number?")

    email = F.EmailField('Email')
    email_error = F.TextField('Email Error')

    languages = F.MultipleSelectField('Languages')
    notes = F.TextField('Notes')

    legacy_first_date_submitted = F.DateField('Legacy First Date Submitted')
    legacy_last_date_submitted = F.DateField('Legacy Last Date Submitted')

    form_submissions = F.LinkField('Form Submissions', FormSubmission)

    last_texted = F.DateField('Last Texted')

    Meta = build_meta('Households')

    if TYPE_CHECKING:
        def __init__(self, *, name: str, phone_number: str,
                     phone_is_invalid: bool, phone_is_intl: bool, email: str,
                     email_error: str, languages: List[str], notes: str,
                     legacy_first_date_submitted: date,
                     legacy_last_date_submitted: date,
                     form_submissions: List[FormSubmission]): ...


class Request(Model):
    household = F.SingleLinkField('Household', Household)
    type = F.SelectField('Type')

    legacy_date_submitted = F.DateField('Legacy Date Submitted')
    request_opened_at = F.DateField('Request Opened At')

    status = F.SelectField('Status')

    geocode = F.TextField('Geocode')

    Meta = build_meta('Requests')

    if TYPE_CHECKING:
        def __init__(self, *, household: Household, type: str,
                     legacy_date_submitted: date | None = None,
                     geocode: str | None = None): ...



class SocialServiceRequest(Model):
    household = F.SingleLinkField('Household', Household)
    type = F.SelectField('Type')

    legacy_date_submitted = F.DateField('Legacy Date Submitted')
    request_opened_at = F.DateField('Request Opened At', readonly=True)

    status = F.SelectField('Status')

    internet_access = F.MultipleSelectField('Internet Access')
    roof_is_accessible = F.CheckboxField('Roof Accessible?')
    street_address = F.TextField('Street Address')
    city_and_state = F.TextField('City, State')
    zip_code = F.NumberField('Zip Code')
    geocode = F.TextField('Geocode')

    Meta = build_meta('Social Service Requests')

    if TYPE_CHECKING:
        def __init__(self, *, household: Household, type: str,
                     legacy_date_submitted: date | None = None,
                     internet_access: List[str] = [],
                     roof_is_accessible: bool = False): ...
