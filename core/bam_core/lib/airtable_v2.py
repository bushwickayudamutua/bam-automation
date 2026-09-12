from urllib3 import Retry
from typing import List, TYPE_CHECKING
from datetime import date, datetime

from pyairtable import Api
from pyairtable.orm import Model, fields as F
from pyairtable.orm.fields import Field

from bam_core.settings import AIRTABLE_V2_BASE_ID, AIRTABLE_V2_TOKEN


def make_meta(table_name: str):
    return {
        'base_id': AIRTABLE_V2_BASE_ID,
        'api_key': AIRTABLE_V2_TOKEN,
        'table_name': table_name,
        'retry': Retry(total=5, backoff_factor=1)
    }


count_table = Api(AIRTABLE_V2_TOKEN).base(AIRTABLE_V2_BASE_ID).table('Fulfilled Request Count')


class FormSubmission(Model):
    Meta = make_meta('Assistance Request Form Submissions')

    bam_id = F.AutoNumberField('ID')

    # household details
    name = F.TextField('Name')
    phone_number = F.PhoneNumberField('Phone Number')
    email = F.EmailField('Email')
    languages = F.MultipleSelectField('Languages')
    other_languages = F.MultilineTextField('Other Languages')
    notes = F.RichTextField('Notes')

    # address details
    street_address = F.TextField('Street Address')
    city_and_state = F.TextField('City, State')
    zip_code = F.NumberField('Zip Code')

    # essential goods requests
    request_types = F.MultipleSelectField('Request Types')

    furniture_acknowledgement = F.CheckboxField('Furniture Acknowledgement')
    furniture_items = F.MultipleSelectField('Furniture Items')
    bed_details = F.MultipleSelectField('Bed Details')

    # social service requests
    ss_request_types = F.MultipleSelectField('Social Service Requests')

    internet_access = F.MultipleSelectField('Internet Access')
    roof_is_accessible = F.CheckboxField('Roof Accessible?')

    if TYPE_CHECKING:
        def __init__(
            self, *,
            name: str | None = None,
            phone_number: str | None = None,
            email: str | None = None,
            languages: List[str] | None = None,
            other_languages: str | None = None,
            notes: str | None = None,
            street_address: str | None = None,
            city_and_state: str | None = None,
            zip_code: int | None = None,
            request_types: List[str] | None = None,
            furniture_acknowledgement: bool = False,
            furniture_items: List[str] | None = None,
            bed_details: List[str] | None = None,
            kitchen_items: List[str] | None = None,
            ss_request_types: List[str] | None = None,
            internet_access: List[str] | None = None,
            roof_is_accessible: bool = False,
        ): ...


class Household(Model):
    Meta = make_meta('Households')

    bam_id = F.AutoNumberField('ID')
    name = F.TextField('Name')

    phone_number = F.PhoneNumberField('Phone Number')
    phone_is_invalid = F.CheckboxField('Invalid Phone Number?')
    phone_is_intl = F.CheckboxField("Int'l Phone Number?")

    email = F.EmailField('Email')
    email_error = F.TextField('Email Error')

    languages = F.MultipleSelectField('Languages')
    other_languages = F.MultilineTextField('Other Languages')

    notes = F.RichTextField('Notes')

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
            legacy_first_date_submitted: date | None = None,
            legacy_last_date_submitted: date | None = None,
            languages: List[str],
            other_languages: str | None = None,
            notes: str | None = None,
            last_texted: date | None = None,
            last_called: date | None = None,
            needs_delivery: bool = False,
            needs_email_outreach: bool = False
        ): ...


class Request(Model):
    Meta = make_meta('Requests')

    household = F.SingleLinkField('Household', Household)
    status = F.SelectField('Status')
    last_requested = F.DatetimeField('Last Requested')
    legacy_date_submitted = F.DateField('Legacy Date Submitted')
    request_opened_at = F.DateField('Request Opened At', readonly=True)

    type = F.SelectField('Type')

    if TYPE_CHECKING:
        def __init__(
            self, *,
            household: Household,
            type: str,
            status: str = "Open",
            legacy_date_submitted: date | None,
            last_requested: datetime | None,
        ): ...


class FurnitureRequest(Model):
    Meta = make_meta('Furniture Requests')

    household = F.SingleLinkField('Household', Household)
    status = F.SelectField('Status')
    last_requested = F.DatetimeField('Last Requested')
    legacy_date_submitted = F.DateField('Legacy Date Submitted')
    request_opened_at = F.DateField('Request Opened At', readonly=True)

    type = F.SelectField('Type')
    geocode = F.TextField('Geocode')

    if TYPE_CHECKING:
        def __init__(
            self, *,
            household: Household,
            type: str,
            status: str = "Open",
            legacy_date_submitted: date | None,
            last_requested: datetime | None,
            geocode: str | None = None
        ): ...


class SocialServiceRequest(Model):
    Meta = make_meta('Social Service Requests')

    household = F.SingleLinkField('Household', Household)
    status = F.SelectField('Status')
    last_requested = F.DatetimeField('Last Requested')
    legacy_date_submitted = F.DateField('Legacy Date Submitted')
    request_opened_at = F.DateField('Request Opened At', readonly=True)

    type = F.SelectField('Type')

    if TYPE_CHECKING:
        def __init__(
            self, *,
            household: Household,
            type: str,
            status: str = "Open",
            legacy_date_submitted: date | None,
            last_requested: datetime | None
        ): ...


class MeshRequest(Model):
    Meta = make_meta('Mesh Requests')

    household = F.SingleLinkField('Household', Household)
    status = F.SelectField('Status')
    last_requested = F.DatetimeField('Last Requested')
    legacy_date_submitted = F.DateField('Legacy Date Submitted')
    request_opened_at = F.DateField('Request Opened At', readonly=True)

    mesh_history = F.MultilineTextField('MESH History')
    internet_access = F.MultipleSelectField('Internet Access')
    address = F.TextField('Address')
    address_accuracy = F.SelectField('Address Accuracy')
    building_identification_number = F.NumberField('Building Identification Number')
    street_address = F.TextField('Street Address')
    city_and_state = F.TextField('City, State')
    zip_code = F.NumberField('Zip Code')

    if TYPE_CHECKING:
        def __init__(
            self, *,
            household: Household,
            status: str = "Open",
            mesh_history: str | None = None,
            legacy_date_submitted: date | None,
            last_requested: datetime | None,
            internet_access: List[str] | None = None,
            address: str | None = None,
            address_accuracy: str | None = None,
            building_identification_number: int | None = None,
            street_address: str | None = None,
            city_and_state: str | None = None,
            zip_code: int | None = None,
        ): ...

