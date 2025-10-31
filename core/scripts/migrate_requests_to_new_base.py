import argparse
from collections import defaultdict
import copy

from bam_core.settings import AIRTABLE_BASE_ID, AIRTABLE_TOKEN
from bam_core.lib.airtable import Airtable
from bam_core.lib.airtable_v2 import (
    FormSubmission,
    Household,
    Request,
    SocialServiceRequest,
)
from bam_core.utils.phone import (
    format_phone_number,
    is_international_phone_number,
)
from bam_core.utils.retry import retry
from bam_core.utils.email import format_email, NO_EMAIL_ERROR
from bam_core.functions.analyze_fulfilled_requests import (
    AnalyzeFulfilledRequests,
)
from bam_core.constants import (
    PHONE_FIELD,
    DATE_SUBMITTED_FIELD,
    BED_REQUESTS_SCHEMA,
    FURNITURE_REQUEST_BED,
    EG_REQUEST_FURNITURE,
    FURNITURE_REQUESTS_SCHEMA,
    KITCHEN_REQUESTS_SCHEMA,
    EG_REQUEST_KITCHEN_SUPPLIES,
    SOCIAL_SERVICES_REQUESTS_SCHEMA,
)

########################################
#  Setup Reference To OG Airtable Base #
########################################

at_og = Airtable(base_id=AIRTABLE_BASE_ID, token=AIRTABLE_TOKEN)


#######################################
#  Initialize Snapshot Analysis FX    #
#######################################
# NOTE: We use the AnalyzeFulfilledRequests class to get the most recent snapshot of each record.
# This is mostly a matter of convenience, since it already has the logic to identify open requests.
# We could also pull the records directly from the Airtable API, but that would require more work lol.

afr = AnalyzeFulfilledRequests()
afr.use_cache = True


#######################################
#  Fetch Open Requests Per Household  #
#######################################


def extract_open_requests_per_household():
    """
    Get all open requests per household from digital ocean snapshots.
    :return: A dictionary of household records, where the key is the phone number
    and the value is a list of records for that household.
    """
    households = defaultdict(list)
    # get all snapshots
    grouped_records = afr.get_grouped_records()

    # get the last snapshot for each record
    for record_id, snapshot in afr.get_last_snapshots(grouped_records):

        # identify the open requests for the snapshot
        open_requests = afr.get_open_requests_for_snapshot(record_id, snapshot)

        # if there are open requests, add them to the household
        # and format the phone number
        # only add the household if there are open requests
        # and the phone number is valid
        if len(open_requests) > 0 and PHONE_FIELD in snapshot:
            snapshot["Open Requests"] = [r["Item"] for r in open_requests]
            phone_number = format_phone_number(snapshot[PHONE_FIELD])
            if phone_number:
                households[phone_number].append(snapshot)
    return households


#######################################
#   Generic Transformation Functions  #
#######################################


def select_first(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    return {new_field_name: records[0].get(old_field_name)}


def select_first_non_null(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    for record in records:
        if record.get(old_field_name):
            return {new_field_name: record.get(old_field_name)}
    return {}


def set_true(old_field_name: str, new_field_name: str, records: list[dict]):
    return {new_field_name: True}


def set_empty(old_field_name: str, new_field_name: str, records: list[dict]):
    return {new_field_name: ""}


############################################
#  Field-Specific Transformation Functions #
############################################


def transform_zip_code(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    """
    Attempt to format the zip code into a 5 digit integer.
    If it fails, set it to None.
    """
    # we only migrate valid zip codes
    output = select_first_non_null(old_field_name, new_field_name, records)
    zip_code = output.get(new_field_name)

    # attempt to format the zip code #
    # remove all non-digit characters
    zip_code = "".join([c for c in str(zip_code).strip() if c.isdigit()])
    # Take the first 5 digits
    if len(zip_code) > 5:
        zip_code = zip_code[:5]

    try:
        # attempt to convert to int
        output[new_field_name] = int(zip_code)
    except (ValueError, KeyError):
        # otherwise set it to None
        output[new_field_name] = None

    return output


def transform_date_submitted(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    """
    Create two new fields: "Legacy First Date Submitted" and "Legacy Last Date Submitted"
    representing the first and last date a request was submitted for the household.
    """
    return {
        f"Legacy First {new_field_name}": min(
            [r[old_field_name] for r in records]
        ).split("T")[0],
        f"Legacy Last {new_field_name}": max(
            [r[old_field_name] for r in records]
        ).split("T")[0],
    }


def transform_invalid_phone_number(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    """
    We're only migrating valid phone numbers, so we set this field to False for all records.
    """
    return {new_field_name: False}


def transform_intl_phone_number(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    """
    Check if first phone number is international
    """
    return {
        new_field_name: is_international_phone_number(
            records[0].get(PHONE_FIELD)
        )
    }


def transform_email(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    """
    If there are valid emails, set the new field to the first valid email
    otherwise set it to an empty string.
    """
    #
    email = ""
    # only merge valid emails
    email_error = str(NO_EMAIL_ERROR)
    for r in records:
        if r.get(old_field_name):
            email_output = format_email(r.get(old_field_name))
            email = email_output.get("email")
            email_error = email_output.get("error")
            if not email_error:
                return {
                    new_field_name: email_output.get("email"),
                    "Email Error": email_error,
                }

    return {new_field_name: email, "Email Error": email_error}


def transform_lists(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    """
    Given a list of records, merge all the values of the old field into a single list
    and remove duplicates.
    """
    all_items = set()
    for r in records:
        all_items.update(r.get(old_field_name, []))
    return {new_field_name: list(all_items)}


def transform_languages(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    """
    Transform the languages field into a single list of languages.
    Also apply a mapping to the languages to map from the old names to the new names.
    """

    LANGUAGE_MAPPING = {
        "Chino Toishanese / Toishanese / 台山话": "Chino Toishanés / Toishanese / 台山话",
        "Chino Cantonese / Cantonese / 广东话": "Chino Cantonés / Cantonese / 广东话",
        "Arabic / 阿拉伯語": "Árabe / Arabic / 阿拉伯語",
        "Portuguese / 葡萄牙語": "Portugués / Portuguese / 葡萄牙語",
        "Portuguese": "Portugués / Portuguese / 葡萄牙語",
        "Otro / Other / 别的方言": "Otro / Other / 其他語言",
        "Haitian Creole / French Creole / 法屬歸融語": "Criollo Haitiano / Haitian Creole / 法屬歸融語",
    }

    output = transform_lists(old_field_name, new_field_name, records)
    # apply language mapping and deduplicate
    output[new_field_name] = list(
        set(
            [
                LANGUAGE_MAPPING.get(item, item)
                for item in output[new_field_name]
            ]
        )
    )
    return output


def transform_internet_access(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    """
    Transform the internet access field into a single list of internet access requests.
    Also apply a mapping to the internet access requests to map from the old names to the new names.
    """
    INTERNET_MAPPING = {
        "El red es lento / My network is slow": "El red es lento / My network is slow / 我的網絡很慢",
        "El red es caro / My internet is expensive": "El red es caro / My internet is expensive / 我的網絡很貴",
        "No tengo acceso al red / I don't have internet access at all": "No tengo acceso al red / I don't have internet access at all / 我無法上網",
        "Lo accedo con mi cellular / I access it with my cell": "Lo accedo con mi cellular / I access it with my cell / 我只能使用手機網絡上網",
        "Uso el red público afuera / I use public internet access": "Uso el red público afuera / I use public internet access / 我只能使用公共網絡上網",
    }
    # we only migrate valid internet access
    output = transform_lists(old_field_name, new_field_name, records)
    # apply internet mapping
    output[new_field_name] = list(
        set(
            [
                INTERNET_MAPPING.get(item, item)
                for item in output[new_field_name]
            ]
        )
    )
    return output


def transform_roof_accessible(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    """
    Transform the roof access field into a single boolean value by checking if
    any of the records have the tag "Tengo acceso de mi techo / Roof access in my building".
    """
    tag = "Tengo acceso de mi techo / Roof access in my building"

    return {
        new_field_name: any(
            [tag in r.get(old_field_name, []) for r in records]
        )
    }


def transform_case_notes(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    """
    Merge case notes into a single value and add a link to the original
    assistance request record.
    """
    case_notes = ""
    for r in records:
        date_submitted = r.get(DATE_SUBMITTED_FIELD)
        link = at_og.get_assistance_request_link(r["id"])
        notes = r.get(old_field_name)
        if notes:
            note_lines = "\n".join(
                [f"    - {n.strip()}" for n in notes.split("\n") if n.strip()]
            )
            case_notes += f"- [{date_submitted[0:10]}]({link})\n"
            case_notes += note_lines
            case_notes += "\n\n"
    return {
        new_field_name: case_notes,
    }


#######################################
#   Open Requests Transformation      #
#######################################


def transform_open_requests(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    """
    We create the "Open Requests" field when we get all open requests per household; It doesn't exist in the old schema.
    We then:
    1. Merge all the open requests into one list
    2. Remove duplicates
    3. Detect instances where sub request types are present and split them into their own fields
    """
    # declare schema of request sub-items
    REQUEST_SUB_ITEMS = [
        {
            "new_request_type": "Cama / Bed / 床",
            "old_request_type": FURNITURE_REQUEST_BED,
            "items": list(BED_REQUESTS_SCHEMA["items"].keys()),
            "items_output_field": "Bed Details",
            "request_type_output_field": "Furniture Items",
        },
        {
            "new_request_type": "Muebles / Furniture / 家具",
            "old_request_type": EG_REQUEST_FURNITURE,
            "items": list(FURNITURE_REQUESTS_SCHEMA["items"].keys()),
            "items_output_field": "Furniture Items",
            "request_type_output_field": "Request Types",
        },
        {
            "new_request_type": "Cosas de Cocina / Kitchen Supplies / 廚房用品",
            "old_request_type": EG_REQUEST_KITCHEN_SUPPLIES,
            "items": list(KITCHEN_REQUESTS_SCHEMA["items"].keys()),
            "items_output_field": "Kitchen Items",
            "request_type_output_field": "Request Types",
        },
        {
            "new_request_type": None,
            "old_request_type": None,
            "items": list(SOCIAL_SERVICES_REQUESTS_SCHEMA["items"].keys()),
            "items_output_field": "Social Service Requests",
            "request_type_output_field": None,
        },
    ]

    # exclude these items from migration
    EXCLUDE_ITEMS = [
        "Asistencia para mascotas / Pet Assistance / 寵物協助",
        "Comida de mascota / Pet Food / 寵物食品",
    ]

    # rename these items
    ITEM_MAPPING = {
        "Otras / Other / 其他家具": "Otras Muebles / Other Furniture / 其他家具",
        "Otras / Other / 其他廚房用品": "Otras Cosas de Cocina / Other Kitchen Items / 其他廚房用品",
    }

    # get the unique set of all items
    all_items = list(
        set(
            [
                item.strip()
                for r in records
                for item in r.get(old_field_name, [])
            ]
        )
    )

    # filter out items we aren't migrating and "Historical" items
    all_items = [
        item
        for item in all_items
        if "historical" not in item.lower() and item not in EXCLUDE_ITEMS
    ]

    # make a copy of the list to remove items from
    all_items_copy = all_items.copy()

    output = defaultdict(list)
    for item in all_items:
        # first check for sub-items and remove them from the top-level list
        for sub_item in REQUEST_SUB_ITEMS:
            # unpack sub_item
            new_request_type = sub_item["new_request_type"]
            old_request_type = sub_item["old_request_type"]
            sub_items = sub_item["items"]
            items_output_field = sub_item["items_output_field"]
            request_type_output_field = sub_item["request_type_output_field"]

            # merge top-level request type
            if old_request_type and item == old_request_type:
                if new_request_type not in output.get(
                    request_type_output_field, []
                ):
                    output[request_type_output_field].append(new_request_type)
                # remove the item from the top-level list
                if item in all_items_copy:
                    all_items_copy.remove(item)

            elif item in sub_items:
                #
                # add the top-level request type if not already present
                if new_request_type and new_request_type not in output.get(
                    request_type_output_field, []
                ):
                    output[request_type_output_field].append(new_request_type)

                # apply item mapping if present
                if item in ITEM_MAPPING:
                    new_item = ITEM_MAPPING[item]
                    old_item = copy.deepcopy(item)

                    # add the new item to the output list
                    output[items_output_field].append(new_item)

                    # remove the old item from the top-level list
                    if old_item in all_items_copy:
                        all_items_copy.remove(old_item)

                else:
                    # add the item to the output list
                    output[items_output_field].append(item)

                    # remove the item from the top-level list
                    if item in all_items_copy:
                        all_items_copy.remove(item)

    # add any remaining items to the top-level list
    output[new_field_name].extend(all_items_copy)

    return output


#########################################
# Transform Households                  #
#########################################


def transform_household_records(household_records: list[dict]) -> dict:
    """
    Given a list of household records, transform them into a single record
    by applying a series of transformation functions to each field.
    :param household_records: A list of household records
    :return: A single transformed household record
    """
    # og schema:new schema
    FIELD_MAPPING = {
        "First Name": {
            "new_field": "Name",
            "transform_fx": select_first_non_null,
        },
        PHONE_FIELD: {"new_field": PHONE_FIELD, "transform_fx": select_first},
        "Invalid Phone Number?": {
            "new_field": "Invalid Phone Number?",
            "transform_fx": transform_invalid_phone_number,
        },
        "Intl Phone Number?": {
            "new_field": "Int'l Phone Number?",
            "transform_fx": transform_intl_phone_number,
        },
        # includes both Email and Email Error
        "Email": {"new_field": "Email", "transform_fx": transform_email},
        "Language": {
            "new_field": "Languages",
            "transform_fx": transform_languages,
        },
        "Current Address": {
            "new_field": "Street Address",
            "transform_fx": select_first_non_null,
        },
        "Current Address - City, State": {
            "new_field": "City, State",
            "transform_fx": select_first_non_null,
        },
        "Current Address - Zip Code": {
            "new_field": "Zip Code",
            "transform_fx": transform_zip_code,
        },
        "Furniture Acknowledgement": {
            "new_field": "Furniture Acknowledgement",
            "transform_fx": set_true,
        },
        "Geocode": {
            "new_field": "Geocode",
            "transform_fx": select_first_non_null,
        },
        "Open Requests": {
            "new_field": "Request Types",
            "transform_fx": transform_open_requests,
        },
        "Internet Access": {
            "new_field": "Internet Access",
            "transform_fx": transform_internet_access,
        },
        "MESH - To confirm during outreach (before install)": {
            "new_field": "Roof Accessible?",
            "transform_fx": transform_roof_accessible,
        },
        "Case Notes": {
            "new_field": "Notes",
            "transform_fx": transform_case_notes,
        },
        # Creates First Date Submitted and Last Date Submitted fields
        DATE_SUBMITTED_FIELD: {
            "new_field": DATE_SUBMITTED_FIELD,
            "transform_fx": transform_date_submitted,
        },
    }

    # sort records by Date Submitted
    records = list(
        sorted(
            household_records,
            key=lambda x: x[DATE_SUBMITTED_FIELD],
            reverse=True,
        )
    )
    # transform/merge fields
    transformed_record = {}
    for old_field_name, mapping in FIELD_MAPPING.items():
        new_field_name = mapping["new_field"]
        transform_fx = mapping["transform_fx"]
        try:
            transformed_record.update(
                transform_fx(old_field_name, new_field_name, records)
            )
        except Exception as e:
            raise Exception(
                f"Error transforming {old_field_name} into {new_field_name}: {e}"
            )
    return transformed_record


def transform_households(households: dict[str, list[dict]]) -> list[dict]:
    """
    Given a dictionary of households, transform each household into a single record
    by applying a series of transformation functions to each field.
    :param households: A dictionary of households, where the key is the phone number
    and the value is a list of records for that household.
    :return: A list of transformed household records
    """
    output = []
    for records in households.values():
        output.append(transform_household_records(records))
    return output


#######################################
#   Airtable Record Creation          #
#######################################


@retry(attempts=5, wait=1, backoff=2)
def create_form_submission_record(record: dict):
    """
    Create a form submission record from the transformed legacy assistance request record.
    :param record: The legacy assistance request record
    :return: The form submission
    """
    submission = FormSubmission(
        name=record['Name'],
        phone_number=record[PHONE_FIELD],
        email=record['Email'],
        languages=record['Languages'],
        notes=record['Notes'],
        street_address=record['Street Address'],
        city_and_state=record['City, State'],
        zip_code=record['Zip Code'],
        request_types=record['Request Types'],
        furniture_acknowledgement=record['Furniture Acknowledgement'],
        furniture_items=record['Furniture Items'],
        bed_details=record['Bed Details'],
        kitchen_items=record['Kitchen Items'],
        ss_request_types=record['Social Service Requests'],
        internet_access=record['Internet Access'],
        roof_is_accessible=record['Roof Accessible?'],
        legacy_first_date_submitted=record['Legacy First Date Submitted'],
        legacy_last_date_submitted=record['Legacy Last Date Submitted'])

    submission.save()

    return submission


@retry(attempts=5, wait=1, backoff=2)
def create_household_record(
    record: dict,
    form_submission: FormSubmission,
) -> Household:
    """
    Create a household record from the transformed legacy assistance request record.
    :param record: The legacy assistance request record
    :param form_submission_id: The form submission ID to link to the household
    """

    # Create it this way instead of passing kwargs to Household() because
    # the type hints can't help you if you do that
    household = Household(
        name=record['Name'],
        phone_number=record[PHONE_FIELD],
        phone_is_invalid=record['Invalid Phone Number?'],
        phone_is_intl=record["Int'l Phone Number?"],
        email=record['Email'],
        email_error=record['Email Error'],
        languages=record['Languages'],
        notes=record['Notes'],
        legacy_first_date_submitted=record['Legacy First Date Submitted'],
        legacy_last_date_submitted=record['Legacy Last Date Submitted'],
        # NOTE: These need to be stored in the relevant request records
        # street_address=record['Street Address'],
        # city_and_state=record['City, State'],
        # zip_code=record['Zip Code'],
        # geocode=record['Geocode'],
        form_submissions=[form_submission])
    household.save()

    return household


@retry(attempts=5, wait=1, backoff=2)
def create_requests_records(record: dict, household: Household):
    """
    Create a list of requests records from the transformed legacy assistance request record.
    :param record: The legacy assistance request record
    :return: A list of requests
    """
    TYPES_TO_EXCLUDE = [
        "Muebles / Furniture / 家具",
        "Cosas de Cocina / Kitchen Supplies / 廚房用品",
        "Cama / Bed / 床",
    ]

    # flatten and dedupe the list of request types
    req_types: set[str] = set()
    req_types.update(record.get("Request Types", []))
    req_types.update(record.get("Furniture Items", []))
    req_types.update(record.get("Kitchen Items", []))
    req_types.update(record.get("Bed Details", []))

    # build requests
    requests = []
    for req_type in req_types:
        if req_type in TYPES_TO_EXCLUDE:
            continue
        request = Request(type=req_type, household=household)
        requests.append(request)

    # write to Airtable
    Request.batch_save(requests)

    return requests


@retry(attempts=5, wait=1, backoff=2)
def create_ss_requests_records(record: dict, household: Household):
    """
    Create a list of social service requests records from the transformed legacy assistance request record.
    :param record: The legacy assistance request record
    :return: A list of social service requests
    """
    INTERNET_REQUEST_TYPE = "Internet de bajo costo en casa / Low-Cost Internet at home / 網絡連結協助"

    # dedupe the list of request types
    req_types = set(record.get("Social Service Requests", []))

    # build requests
    requests = []
    for req_type in req_types:
        request = SocialServiceRequest(type=req_type, household=household)
        if req_type == INTERNET_REQUEST_TYPE:
            request.internet_access = record.get('Internet Access', [])
            request.roof_is_accessible = record.get('Roof Accessible?', False)
        requests.append(request)

    # write to Airtable
    SocialServiceRequest.batch_save(requests)

    return requests


def load_household(record: dict):
    """
    Migrate an assistance request from the old base to the new base,
    creating records in all the necessary tables.
    :param record: The legacy assistance request record
    :return: None
    """
    form_submission_id = create_form_submission_record(record)
    # create the household record
    household = create_household_record(record, form_submission_id)
    create_requests_records(record, household)
    create_ss_requests_records(record, household)


#######################################
#   CLI                               #
#######################################


def main():
    parser = argparse.ArgumentParser(
        description="""
            Migrate requests from old base to new base. MAKE SURE YOU HAVE YOUR .env FILE SET UP CORRECTLY.
        """
    )
    parser.add_argument(
        "--start-at",
        type=int,
        default=1,
        help="Start at this record number (for debugging)",
    )
    args = parser.parse_args()
    legacy_requests = extract_open_requests_per_household()
    transformed_requests = transform_households(legacy_requests)
    transformed_requests_subset = transformed_requests[args.start_at - 1:]
    print(f"Total records to migrate: {len(transformed_requests_subset)}")
    for i, household_request in enumerate(
        transformed_requests_subset, start=args.start_at
    ):
        if i % 100 == 0:
            print(
                f"Migrated {i} records. {len(transformed_requests_subset) - i} records left."
            )
        try:
            load_household(household_request)
        except Exception as e:
            print("Restart at:", i)
            raise e


if __name__ == "__main__":
    main()
