import argparse
from collections import defaultdict
import copy
from datetime import datetime
from dateutil import parser as date_parser
import pandas as pd

from bam_core.settings import (
    AIRTABLE_BASE_ID,
    AIRTABLE_TOKEN,
    AIRTABLE_V2_BASE_ID,
    AIRTABLE_V2_TOKEN,
)
from bam_core.lib.airtable import Airtable
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

#######################################
#  Setup References To Airtable Bases #
#######################################

at_og = Airtable(base_id=AIRTABLE_BASE_ID, token=AIRTABLE_TOKEN)
at_v2 = Airtable(base_id=AIRTABLE_V2_BASE_ID, token=AIRTABLE_V2_TOKEN)
form_submission_table = at_v2.get_table("Assistance Request Form Submissions")
ss_requests_table = at_v2.get_table("Social Service Requests")
requests_table = at_v2.get_table("Requests")
households_table = at_v2.get_table("Households")


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


def select_oldest_request(item_df):
    item_df.sort_values(by=DATE_SUBMITTED_FIELD, ascending=True, inplace=True)
    item_df.drop_duplicates(subset="item", keep='first', inplace=True)
    item_df.reset_index(drop=True, inplace=True)
    return item_df


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

    def item_df(r, item):
        df = pd.DataFrame({"item": [item]})
        df.insert(column=DATE_SUBMITTED_FIELD, value=r.get(DATE_SUBMITTED_FIELD, []), loc = 0)
        return df

    all_items_df = pd.concat([
        item_df(r, item)
        for r in records for item in r.get(old_field_name)
    ])

    # pick oldest request of each type:
    all_items_df = select_oldest_request(all_items_df)

    # filter out items we aren't migrating and "Historical" items
    not_historical = pd.Series(["historical" not in item.lower() for item in all_items_df.get("item",[])])
    not_excluded_item = ~all_items_df.get("item",[]).isin(EXCLUDE_ITEMS)
    keep_idx = not_historical & not_excluded_item
    all_items_df = all_items_df[keep_idx]

    # make a copy of the list to remove items from
    all_items_df_copy = all_items_df.copy()

    output = defaultdict(pd.DataFrame)
    for item, date_submitted in zip(all_items_df.get("item",[]), all_items_df.get(DATE_SUBMITTED_FIELD,[])):
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
                if new_request_type:
                    new_item_row = pd.DataFrame({"item": [new_request_type], DATE_SUBMITTED_FIELD: [date_submitted]})
                    output[request_type_output_field] = pd.concat([output[request_type_output_field], new_item_row])
                # remove the item from the top-level list
                keep_idx = all_items_df_copy.get("item",[]) != item
                all_items_df_copy = all_items_df_copy[keep_idx]
            elif item in sub_items:
                # add the top-level request type if not already present
                if new_request_type:
                    new_item_row = pd.DataFrame({"item": [new_request_type], DATE_SUBMITTED_FIELD: [date_submitted]})
                    output[request_type_output_field] = pd.concat([output[request_type_output_field], new_item_row])
                # apply item mapping if present
                if item in ITEM_MAPPING:
                    new_item = ITEM_MAPPING[item]
                    old_item = copy.deepcopy(item)
                    # add the new item to the output list
                    new_item_row = pd.DataFrame({"item": [new_item], DATE_SUBMITTED_FIELD: [date_submitted]})
                    output[items_output_field] = pd.concat([output[items_output_field], new_item_row])
                    # remove the old item from the top-level list
                    keep_idx = all_items_df_copy.get("item",[]) != old_item
                    all_items_df_copy = all_items_df_copy[keep_idx]
                else:
                    # add the item to the output list
                    new_item_row = pd.DataFrame({"item": [item], DATE_SUBMITTED_FIELD: [date_submitted]})
                    output[items_output_field] = pd.concat([output[items_output_field], new_item_row])
                    # remove the item from the top-level list
                    keep_idx = all_items_df_copy.get("item",[]) != item
                    all_items_df_copy = all_items_df_copy[keep_idx]

    # add any remaining items to the top-level list
    output[new_field_name] = pd.concat([output[new_field_name], all_items_df_copy])

    # pick oldest request of each type:
    output = {name: select_oldest_request(item_df) for name, item_df in output.items()}

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
    :return: The form submission ID
    """
    # Fields to exclude from the request table.
    FORM_SUBMISSION_EXCLUDE_FIELDS = [
        "Invalid Phone Number?",
        "Email Error",
        "Int'l Phone Number?",
        "Geocode",
    ]

    form_submission = {
        k: v
        for k, v in record.items()
        if k not in FORM_SUBMISSION_EXCLUDE_FIELDS
    }
    form_submission_response = form_submission_table.create(form_submission)
    return form_submission_response["id"]


@retry(attempts=5, wait=1, backoff=2)
def create_requests_records(record: dict):
    """
    Create a list of requests records from the transformed legacy assistance request record.
    :param record: The legacy assistance request record
    :return: A list of request IDs
    """
    TYPES_TO_EXCLUDE = [
        "Muebles / Furniture / 家具",
        "Cosas de Cocina / Kitchen Supplies / 廚房用品",
        "Cama / Bed / 床",
    ]

    # flatten the list of requests
    all_reqs = pd.concat([
        record.get("Request Types"),
        record.get("Furniture Items"),
        record.get("Kitchen Items"),
        record.get("Bed Details"),
    ], ignore_index=True)

    # remove excluded types and pick oldest request of each type
    keep_idx = ~all_reqs.get("item",[]).isin(TYPES_TO_EXCLUDE)
    all_reqs = all_reqs[keep_idx]
    all_reqs = select_oldest_request(all_reqs)
    
    request_records = [
        {"Type": r, "Legacy " + DATE_SUBMITTED_FIELD: d} for r,d in zip(all_reqs.get("item",[]), all_reqs.get(DATE_SUBMITTED_FIELD,[]))
    ]
    requests_response = requests_table.batch_create(request_records)
    return [r["id"] for r in requests_response]


@retry(attempts=5, wait=1, backoff=2)
def create_ss_requests_records(record: dict):
    """
    Create a list of social service requests records from the transformed legacy assistance request record.
    :param record: The legacy assistance request record
    :return: A list of social service request IDs
    """
    ss_reqs = record.get("Social Service Requests", [])
    ss_records = []
    for req in ss_reqs:
        ss_record = {
            "Type": req,
        }
        if (
            req
            == "Internet de bajo costo en casa / Low-Cost Internet at home / 網絡連結協助"
        ):
            ss_record["Internet Access"] = record.get("Internet Access", [])
            ss_record["Roof Accessible?"] = record.get(
                "Roof Accessible?", False
            )
        ss_records.append(ss_record)

    ss_requests_response = ss_requests_table.batch_create(ss_records)
    return [r["id"] for r in ss_requests_response]


@retry(attempts=5, wait=1, backoff=2)
def create_household_record(
    record: dict,
    request_ids: list[str],
    ss_request_ids: list[str],
    form_submission_id: str,
):
    """
    Create a household record from the transformed legacy assistance request record.
    :param record: The legacy assistance request record
    :param request_ids: The list of request IDs to link to the household
    :param ss_request_ids: The list of social service request IDs to link to the household
    :param form_submission_id: The form submission ID to link to the household
    """

    HOUSEHOLD_INCLUDE_FIELDS = [
        "Name",
        PHONE_FIELD,
        "Invalid Phone Number?",
        "Int'l Phone Number?",
        "Email",
        "Email Error",
        "Languages",
        "Notes",
        "Legacy First Date Submitted",
        "Legacy Last Date Submitted",
        "Street Address",
        "City, State",
        "Zip Code",
        "Geocode",
    ]

    household = {
        k: v for k, v in record.items() if k in HOUSEHOLD_INCLUDE_FIELDS
    }
    household["Requests"] = request_ids
    household["Social Service Requests"] = ss_request_ids
    household["Form Submissions"] = [form_submission_id]
    households_table.create(household)


def load_household(record: dict):
    """
    Migrate an assistance request from the old base to the new base,
    creating records in all the necessary tables.
    :param record: The legacy assistance request record
    :return: None
    """
    form_submission_id = create_form_submission_record(record)
    ss_request_ids = create_ss_requests_records(record)
    request_ids = create_requests_records(record)
    # create the household record
    create_household_record(
        record, request_ids, ss_request_ids, form_submission_id
    )


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
    transformed_requests_subset = transformed_requests[args.start_at - 1 :]
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

