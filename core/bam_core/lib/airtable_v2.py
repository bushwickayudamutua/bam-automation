from typing import List, TYPE_CHECKING
from datetime import date

from pyairtable.orm import Model, fields as F

from bam_core import settings


class BamModelMeta(type):
    @property
    def Meta(cls):
        return {
            'base_id': settings.AIRTABLE_V2_BASE_ID,
            'api_key': settings.AIRTABLE_V2_TOKEN,
            'table_name': cls.table_name,
        }


class BamModel(Model, metaclass=BamModelMeta):
    table_name = 'Table'


class FormSubmission(BamModel):
    table_name = 'Assistance Request Form Submissions'

    bam_id = F.AutoNumberField('ID')

    # household details
    name = F.TextField('Name')
    phone_number = F.PhoneNumberField('Phone Number')
    email = F.EmailField('Email')
    languages = F.MultipleSelectField('Languages')
    other_languages = F.TextField('Other Languages')
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

    if TYPE_CHECKING:
        def __init__(
            self, *,
            name: str,
            phone_number: str,
            email: str,
            languages: List[str],
            other_languages: str,
            notes: str,
            street_address: str,
            city_and_state: str,
            zip_code: int,
            request_types: List[str],
            furniture_acknowledgement: bool,
            furniture_items: List[str],
            bed_details: List[str],
            kitchen_items: List[str],
            ss_request_types: List[str],
            internet_access: List[str],
            roof_is_accessible: bool,
        ): ...


class Household(BamModel):
    table_name = 'Households'

    bam_id = F.AutoNumberField('ID')
    name = F.TextField('Name')

    phone_number = F.PhoneNumberField('Phone Number')
    phone_is_invalid = F.CheckboxField('Invalid Phone Number?')
    phone_is_intl = F.CheckboxField("Int'l Phone Number?")

    email = F.EmailField('Email')
    email_error = F.TextField('Email Error')

    languages = F.MultipleSelectField('Languages')
    other_languages = F.TextField('Other Languages')

    notes = F.TextField('Notes')

    legacy_first_date_submitted = F.DateField('Legacy First Date Submitted')
    legacy_last_date_submitted = F.DateField('Legacy Last Date Submitted')

    last_texted = F.DateField('Last Texted')
    last_called = F.DateField('Last Called')

    needs_delivery = F.CheckboxField('Needs Delivery')
    needs_email_outreach = F.CheckboxField('Needs Email Outreach')

    if TYPE_CHECKING:
        def __init__(
            self, *,
            name: str,
            phone_number: str,
            phone_is_invalid: bool,
            phone_is_intl: bool,
            email: str,
            email_error: str,
            legacy_first_date_submitted: date,
            legacy_last_date_submitted: date,
            languages: List[str],
            other_languages: str | None = None,
            notes: str | None = None,
            last_texted: date | None = None,
            last_called: date | None = None,
            needs_delivery: bool = False,
            needs_email_outreach: bool = False
        ): ...


class BaseRequest(BamModel):
    household = F.SingleLinkField('Household', Household)

    last_requested = F.DateField('Last Requested')
    legacy_date_submitted = F.DateField('Legacy Date Submitted')
    request_opened_at = F.DateField('Request Opened At')

    status = F.SelectField('Status')


class Request(BaseRequest):
    table_name = 'Requests'

    type = F.SelectField('Type')
    geocode = F.TextField('Geocode')

    if TYPE_CHECKING:
        def __init__(
            self, *,
            household: Household,
            type: str,
            status: str = "Open",
            legacy_date_submitted: date | None,
            last_requested: date | None,
            geocode: str | None = None
        ): ...

class SocialServiceRequest(BaseRequest):
    table_name = 'Social Service Requests'

    type = F.SelectField('Type')

    if TYPE_CHECKING:
        def __init__(
            self, *,
            household: Household,
            type: str,
            status: str = "Open",
            legacy_date_submitted: date | None,
            last_requested: date | None
        ): ...


class MeshRequest(BaseRequest):
    table_name = 'Mesh Requests'

    internet_access = F.MultipleSelectField('Internet Access')
    street_address = F.TextField('Street Address')
    city_and_state = F.TextField('City, State')
    zip_code = F.NumberField('Zip Code')

    if TYPE_CHECKING:
        def __init__(
            self, *,
            household: Household,
            status: str = "Open",
            legacy_date_submitted: date | None,
            last_requested: date | None,
            internet_access: List[str] = [],
            street_address: str,
            city_and_state: str,
            zip_code: int
        ): ...
