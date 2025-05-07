import argparse
from collections import defaultdict
import copy
import json

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

at_og = Airtable(base_id=AIRTABLE_BASE_ID, token=AIRTABLE_TOKEN)
at_v2 = Airtable(base_id=AIRTABLE_V2_BASE_ID, token=AIRTABLE_V2_TOKEN)

afr = AnalyzeFulfilledRequests()
afr.use_cache = True


# merge functions
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


def merge_zip_code(
    old_field_name: str, new_field_name: str, records: list[dict]
):
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


def merge_date_submitted(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    return {
        f"Legacy First {new_field_name}": min(
            [r[old_field_name] for r in records]
        ).split("T")[0],
        f"Legacy Last {new_field_name}": max(
            [r[old_field_name] for r in records]
        ).split("T")[0],
    }


def merge_invalid_phone_number(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    # we only migrate valid phone numbers
    return {new_field_name: False}


def merge_intl_phone_number(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    return {
        new_field_name: is_international_phone_number(
            records[0].get(PHONE_FIELD)
        )
    }


def merge_email(old_field_name: str, new_field_name: str, records: list[dict]):
    # If there are valid emails, set the new field to the first valid email
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


def merge_all_lists(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    all_items = set()
    for r in records:
        all_items.update(r.get(old_field_name, []))
    return {new_field_name: list(all_items)}


def merge_languages(
    old_field_name: str, new_field_name: str, records: list[dict]
):

    LANGUAGE_MAPPING = {
        "Chino Toishanese / Toishanese / 台山话": "Chino Toishanés / Toishanese / 台山话",
        "Chino Cantonese / Cantonese / 广东话": "Chino Cantonés / Cantonese / 广东话",
        "Arabic / 阿拉伯語": "Árabe / Arabic / 阿拉伯語",
        "Portuguese / 葡萄牙語": "Portugués / Portuguese / 葡萄牙語",
        "Portuguese": "Portugués / Portuguese / 葡萄牙語",
        "Otro / Other / 别的方言": "Otro / Other / 其他語言",
        "Haitian Creole / French Creole / 法屬歸融語": "Criollo Haitiano / Haitian Creole / 法屬歸融語",
    }

    output = merge_all_lists(old_field_name, new_field_name, records)
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


def merge_internet_access(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    INTERNET_MAPPING = {
        "El red es lento / My network is slow": "El red es lento / My network is slow / 我的網絡很慢",
        "El red es caro / My internet is expensive": "El red es caro / My internet is expensive / 我的網絡很貴",
        "No tengo acceso al red / I don't have internet access at all": "No tengo acceso al red / I don't have internet access at all / 我無法上網",
        "Lo accedo con mi cellular / I access it with my cell": "Lo accedo con mi cellular / I access it with my cell / 我只能使用手機網絡上網",
        "Uso el red público afuera / I use public internet access": "Uso el red público afuera / I use public internet access / 我只能使用公共網絡上網",
    }
    # we only migrate valid internet access
    output = merge_all_lists(old_field_name, new_field_name, records)
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


def merge_roof_accessible(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    tag = "Tengo acceso de mi techo / Roof access in my building"

    return {
        new_field_name: any(
            [tag in r.get(old_field_name, []) for r in records]
        )
    }


def merge_case_notes(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    """
    Merge case notes into a single field and add a link to the original assistance request record.
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


def merge_airtable_urls(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    airtable_links = ""
    for r in records:
        if record_id := r.get(old_field_name):
            date_submitted = r.get(DATE_SUBMITTED_FIELD)
            link = at_og.get_assistance_request_link(r[old_field_name])
            airtable_links += f"- [{date_submitted[0:10]}]({link})\n"
    return {new_field_name: airtable_links}


def merge_open_requests(
    old_field_name: str, new_field_name: str, records: list[dict]
):
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


# og schema:new schema
FIELD_MAPPING = {
    "First Name": {"new_field": "Name", "merge_fx": select_first_non_null},
    PHONE_FIELD: {"new_field": PHONE_FIELD, "merge_fx": select_first},
    "Invalid Phone Number?": {
        "new_field": "Invalid Phone Number?",
        "merge_fx": merge_invalid_phone_number,
    },
    "Intl Phone Number?": {
        "new_field": "Int'l Phone Number?",
        "merge_fx": merge_intl_phone_number,
    },
    # includes both Email and Email Error
    "Email": {"new_field": "Email", "merge_fx": merge_email},
    "Language": {"new_field": "Languages", "merge_fx": merge_languages},
    "Current Address": {
        "new_field": "Street Address",
        "merge_fx": select_first_non_null,
    },
    "Current Address - City, State": {
        "new_field": "City, State",
        "merge_fx": select_first_non_null,
    },
    "Current Address - Zip Code": {
        "new_field": "Zip Code",
        "merge_fx": merge_zip_code,
    },
    "Furniture Acknowledgement": {
        "new_field": "Furniture Acknowledgement",
        "merge_fx": set_true,
    },
    "Geocode": {"new_field": "Geocode", "merge_fx": select_first_non_null},
    # We create the "Open Requests" field when we get all open requests per household; It doesn't exist in the old schema.
    # We then:
    # 1. Merge all the open requests into one list
    # 2. Remove duplicates
    # 3. Detect instances where sub request types are present and split them into their own fields
    "Open Requests": {
        "new_field": "Request Types",
        "merge_fx": merge_open_requests,
    },
    "Internet Access": {
        "new_field": "Internet Access",
        "merge_fx": merge_internet_access,
    },
    "MESH - To confirm during outreach (before install)": {
        "new_field": "Roof Accessible?",
        "merge_fx": merge_roof_accessible,
    },
    "Case Notes": {"new_field": "General Notes", "merge_fx": merge_case_notes},
    # "id": {"new_field": "Legacy Airtable Records", "merge_fx": merge_airtable_urls},
    # Creates First Date Submitted and Last Date Submitted fields
    DATE_SUBMITTED_FIELD: {
        "new_field": DATE_SUBMITTED_FIELD,
        "merge_fx": merge_date_submitted,
    },
}

# Fields to exclude from the request table.
FORM_SUBMISSION_EXCLUDE_FIELDS = [
    "Invalid Phone Number?",
    "Email Error",
    "Int'l Phone Number?",
    "Geocode",
]


# Steps:
# 1. Get the most recent snapshot for each record
# 2. For each record get only the open requests
# 3. Replace the existing requests with only the open requests
# 4. Group all the requests by phone number (aka "Household")
# 5. For each Household group, merge/select fields from the requests into one household record.
#    - Follow instructions here: https://docs.google.com/spreadsheets/d/1fBwNU1RSBJtUrp_mjwxYZFgiknfaHU8IXiigAQjuj1I/edit?gid=0#gid=0


# 1. Get the most recent snapshot for each record
# 2. For each record get only the open requests
# 3. Replace the existing requests with only the open requests
# 4. Group all the requests by formatted phone number (aka "Household")
def get_open_requests_by_household():
    households = defaultdict(list)
    """Get all snapshots from the old base"""
    grouped_records = afr.get_grouped_records()
    for record_id, snapshot in afr.get_last_snapshots(grouped_records):
        open_requests = afr.get_open_requests_for_snapshot(record_id, snapshot)
        if len(open_requests) > 0 and PHONE_FIELD in snapshot:
            snapshot["Open Requests"] = [r["Item"] for r in open_requests]
            phone_number = format_phone_number(snapshot[PHONE_FIELD])
            # only allow valid phone numbers
            if phone_number:
                households[phone_number].append(snapshot)
    return households


def merge_household_records(household):
    # sort records by Date Submitted
    records = list(
        sorted(household, key=lambda x: x[DATE_SUBMITTED_FIELD], reverse=True)
    )
    # merge fields
    merged_record = {}
    for old_field_name, mapping in FIELD_MAPPING.items():
        new_field_name = mapping["new_field"]
        merge_fx = mapping["merge_fx"]
        try:
            merged_record.update(
                merge_fx(old_field_name, new_field_name, records)
            )
        except Exception as e:
            raise Exception(
                f"Error merging {old_field_name} into {new_field_name}: {e}"
            )
    return merged_record


def merge_households(households):
    output = []
    for records in households.values():
        output.append(merge_household_records(records))
    return output


def main():
    parser = argparse.ArgumentParser(
        description="Migrate requests from old base to new base. MAKE SURE YOU HAVE YOUR .env FILE SET UP CORRECTLY."
    )
    parser.add_argument(
        "--start-at",
        type=int,
        default=1,
        help="Start at this record number (for debugging)",
    )
    args = parser.parse_args()
    open_requests = get_open_requests_by_household()
    output = merge_households(open_requests)
    filtered_output = output[args.start_at - 1 :]
    print(f"Total records to migrate: {len(filtered_output)}")
    for record in filtered_output:
        form_submission = {
            k: v
            for k, v in record.items()
            if k not in FORM_SUBMISSION_EXCLUDE_FIELDS
        }
        try:
            response = at_v2.get_table(
                "Assistance Request Form Submissions"
            ).create(form_submission)
        except Exception as e:
            print(f"Error creating form submission from record:")
            print(json.dumps(record, indent=2))
            print(f"Error: {e}")
            return
        # TODO: Update the household and request tables by linking to the form submission


if __name__ == "__main__":
    main()
