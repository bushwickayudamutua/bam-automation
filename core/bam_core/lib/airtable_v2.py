from typing import TypedDict

from pyairtable.orm import Model, fields as F

from bam_core import settings


class AirtableV2Meta(TypedDict):
    base_id: str
    api_key: str
    table_name: str

def build_meta(table_name: str) -> AirtableV2Meta:
    return {
        'base_id': settings.AIRTABLE_V2_BASE_ID,
        'api_key': settings.AIRTABLE_V2_TOKEN,
        'table_name': table_name,
    }

class Household(Model):
    name = F.TextField('Name')
    ID = F.AutoNumberField('ID')
    phone_number = F.PhoneNumberField('Phone Number')
    last_texted = F.DateField('Last Texted')

    Meta = build_meta('Households')

class Request(Model):
    household = F.SingleLinkField('Household', Household)
    type = F.SelectField('Type')
    status = F.SelectField('Status')
    request_opened_at = F.DateField('Request Opened At')

    Meta = build_meta('Requests')

class SocialServiceRequest(Model):
    household = F.SingleLinkField('Household', Household)
    type = F.SelectField('Type')
    status = F.SelectField('Status')
    request_opened_at = F.DateField('Request Opened At')

    Meta = build_meta('Social Service Requests')
