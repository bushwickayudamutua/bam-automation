from datetime import date, datetime
from typing import TYPE_CHECKING

from pyairtable import Api
from pyairtable.orm import Model
from pyairtable.orm import fields as F
from urllib3 import Retry

from bam_core.settings import AIRTABLE_V2_BASE_ID, AIRTABLE_V2_TOKEN

if AIRTABLE_V2_BASE_ID is None:
    raise RuntimeError("Missing required environment variable: AIRTABLE_V2_BASE_ID")
if AIRTABLE_V2_TOKEN is None:
    raise RuntimeError("Missing required environment variable: AIRTABLE_V2_TOKEN")


def make_meta(table_name: str):
    return {
        "base_id": AIRTABLE_V2_BASE_ID,
        "api_key": AIRTABLE_V2_TOKEN,
        "table_name": table_name,
        "retry": Retry(total=5, backoff_factor=1),
    }


count_table = (
    Api(AIRTABLE_V2_TOKEN).base(AIRTABLE_V2_BASE_ID).table("Fulfilled Request Count")
)


class FormSubmission(Model):
    Meta = make_meta("Assistance Request Form Submissions")

    bam_id = F.AutoNumberField("ID")

    # household details
    name = F.TextField("Name")
    phone_number = F.PhoneNumberField("Phone Number")
    email = F.EmailField("Email")
    languages = F.MultipleSelectField("Languages")
    other_languages = F.MultilineTextField("Other Languages")
    notes = F.RichTextField("Notes")

    # address details
    street_address = F.TextField("Street Address")
    city_and_state = F.TextField("City, State")
    zip_code = F.NumberField("Zip Code")

    # essential goods requests
    request_types = F.MultipleSelectField("Request Types")

    furniture_acknowledgement = F.CheckboxField("Furniture Acknowledgement")
    furniture_items = F.MultipleSelectField("Furniture Items")
    bed_details = F.MultipleSelectField("Bed Details")

    # social service requests
    ss_request_types = F.MultipleSelectField("Social Service Requests")

    internet_access = F.MultipleSelectField("Internet Access")
    roof_is_accessible = F.CheckboxField("Roof Accessible?")

    # other requests/comments field
    other_requests_and_comments = F.RichTextField("Other Requests and Comments")

    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            name: str | None = None,
            phone_number: str | None = None,
            email: str | None = None,
            languages: list[str] | None = None,
            other_languages: str | None = None,
            notes: str | None = None,
            street_address: str | None = None,
            city_and_state: str | None = None,
            zip_code: int | None = None,
            request_types: list[str] | None = None,
            furniture_acknowledgement: bool = False,
            furniture_items: list[str] | None = None,
            bed_details: list[str] | None = None,
            kitchen_items: list[str] | None = None,
            ss_request_types: list[str] | None = None,
            internet_access: list[str] | None = None,
            roof_is_accessible: bool = False,
        ): ...


class Household(Model):
    Meta = make_meta("Households")

    bam_id = F.AutoNumberField("ID")
    name = F.TextField("Name")

    phone_number = F.PhoneNumberField("Phone Number")
    phone_is_invalid = F.CheckboxField("Invalid Phone Number?")
    phone_is_intl = F.CheckboxField("Int'l Phone Number?")

    email = F.EmailField("Email")
    email_error = F.TextField("Email Error")

    languages = F.MultipleSelectField("Languages")
    other_languages = F.MultilineTextField("Other Languages")

    notes = F.RichTextField("Notes")
    other_requests_and_comments = F.RichTextField("Other Requests and Comments")

    legacy_first_date_submitted = F.DateField("Legacy First Date Submitted")
    legacy_last_date_submitted = F.DateField("Legacy Last Date Submitted")

    last_texted = F.DateField("Last Texted")
    last_called = F.DateField("Last Called")

    needs_delivery = F.CheckboxField("Needs Delivery")
    needs_email_outreach = F.CheckboxField("Needs Email Outreach")

    open_request_types = F.LookupField[str]("Open Request Types")
    
    baby_diapers_requested_at = F.LookupField[date]('Baby Diapers Requested At')
    adult_diapers_requested_at = F.LookupField[date]('Adult Diapers Requested At')
    clothing_requested_at = F.LookupField[date]('Clothing Requested At')
    soap_requested_at = F.LookupField[date]('Soap Requested At')
    pads_requested_at = F.LookupField[date]('Pads Requested At')
    school_supplies_requested_at = F.LookupField[date]('School Supplies Requested At')
    pots_and_pans_requested_at = F.LookupField[date]('Pots & Pans Requested At')
    plates_and_cups_requested_at = F.LookupField[date]('Plates & Cups Requested At')
    
    
    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            name: str,
            phone_number: str,
            phone_is_invalid: bool,
            phone_is_intl: bool,
            email: str,
            email_error: str,
            legacy_first_date_submitted: date | None = None,
            legacy_last_date_submitted: date | None = None,
            languages: list[str],
            other_languages: str | None = None,
            notes: str | None = None,
            last_texted: date | None = None,
            last_called: date | None = None,
            needs_delivery: bool = False,
            needs_email_outreach: bool = False,
        ): ...
    

    def get_requested_date(self, type: str):
        DATE_FIELD_MAP = {
            "Pañales / Baby Diapers / 嬰兒紙尿褲": "baby_diapers_requested_at",
            "Pañales de adultos / Adult Diapers / 成人紙尿褲": "adult_diapers_requested_at",
            "Ropa / Clothing / 服裝": "clothing_requested_at",
            "Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴用品": "soap_requested_at",
            "Productos Femenino - Toallitas / Feminine Products - Pads / 衛生巾": "pads_requested_at",
            "Cosas de Escuela / School Supplies / 學校用品": "school_supplies_requested_at",
            "Ollas y Sartenes / Pots & Pans / 鍋碗瓢盆": "pots_and_pans_requested_at",
            "Platos o Tazas / Plates or Cups / 盘子或杯子": "plates_and_cups_requested_at",
        }
        return getattr(self, DATE_FIELD_MAP.get(type))


class Request(Model):
    Meta = make_meta("Requests")

    household = F.SingleLinkField("Household", Household)
    status = F.SelectField("Status")
    last_requested = F.DatetimeField("Last Requested")
    legacy_date_submitted = F.DateField("Legacy Date Submitted")
    request_opened_at = F.DateField("Request Opened At", readonly=True)

    type = F.SelectField("Type")

    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            household: Household,
            type: str,
            status: str = "Open",
            legacy_date_submitted: date | None,
            last_requested: datetime | None,
        ): ...


class FurnitureRequest(Model):
    Meta = make_meta("Furniture Requests")

    household = F.SingleLinkField("Household", Household)
    status = F.SelectField("Status")
    last_requested = F.DatetimeField("Last Requested")
    legacy_date_submitted = F.DateField("Legacy Date Submitted")
    request_opened_at = F.DateField("Request Opened At", readonly=True)

    type = F.SelectField("Type")
    geocode = F.TextField("Geocode")

    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            household: Household,
            type: str,
            status: str = "Open",
            legacy_date_submitted: date | None,
            last_requested: datetime | None,
            geocode: str | None = None,
        ): ...


class SocialServiceRequest(Model):
    Meta = make_meta("Social Service Requests")

    household = F.SingleLinkField("Household", Household)
    status = F.SelectField("Status")
    last_requested = F.DatetimeField("Last Requested")
    legacy_date_submitted = F.DateField("Legacy Date Submitted")
    request_opened_at = F.DateField("Request Opened At", readonly=True)

    type = F.SelectField("Type")

    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            household: Household,
            type: str,
            status: str = "Open",
            legacy_date_submitted: date | None,
            last_requested: datetime | None,
        ): ...


class MeshRequest(Model):
    Meta = make_meta("Mesh Requests")

    household = F.SingleLinkField("Household", Household)
    status = F.SelectField("Status")
    last_requested = F.DatetimeField("Last Requested")
    legacy_date_submitted = F.DateField("Legacy Date Submitted")
    request_opened_at = F.DateField("Request Opened At", readonly=True)

    mesh_history = F.MultilineTextField("MESH History")
    internet_access = F.MultipleSelectField("Internet Access")
    address = F.TextField("Address")
    address_accuracy = F.SelectField("Address Accuracy")
    building_identification_number = F.NumberField("Building Identification Number")
    street_address = F.TextField("Street Address")
    city_and_state = F.TextField("City, State")
    zip_code = F.NumberField("Zip Code")

    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            household: Household,
            status: str = "Open",
            mesh_history: str | None = None,
            legacy_date_submitted: date | None,
            last_requested: datetime | None,
            internet_access: list[str] | None = None,
            address: str | None = None,
            address_accuracy: str | None = None,
            building_identification_number: int | None = None,
            street_address: str | None = None,
            city_and_state: str | None = None,
            zip_code: int | None = None,
        ): ...
