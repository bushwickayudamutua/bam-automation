from collections import defaultdict

import pandas as pd

from bam_core.settings import (
    AIRTABLE_BASE_ID,
    AIRTABLE_TOKEN,
    AIRTABLE_V2_BASE_ID,
    AIRTABLE_V2_TOKEN,
)
from bam_core.lib.airtable import Airtable
from bam_core.utils.phone import format_phone_number, is_international_phone_number
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


# merge functions
def select_first(old_field_name: str, new_field_name: str, records: list[dict]):
    return {new_field_name: records[0].get(old_field_name)}


def select_first_non_null(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    for record in records:
        if record.get(old_field_name):
            return {new_field_name: record.get(old_field_name)}
    return {}


def merge_date_submitted(old_field_name: str, new_field_name: str, records: list[dict]):
    return {
        f"First {new_field_name}": min([r[old_field_name] for r in records]).split("T")[
            0
        ],
        f"Last {new_field_name}": max([r[old_field_name] for r in records]).split("T")[
            0
        ],
    }


def merge_invalid_phone_number(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    # we only migrate valid phone numbers
    return {new_field_name: False}


def merge_intl_phone_number(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    return {new_field_name: is_international_phone_number(records[0].get(PHONE_FIELD))}


def merge_email(old_field_name: str, new_field_name: str, records: list[dict]):
    # If there are valid emails, set the new field to the first valid email
    email = ""
    email_error = str(NO_EMAIL_ERROR)
    for r in records:
        if r.get("Email Error", "") == "" and r.get(old_field_name):
            email_output = format_email(r.get(old_field_name))
            email = email_output.get("email")
            email_error = email_output.get("error")
            if not email_error:
                return {new_field_name: email_output.get("email"), "Email Error": ""}

    return {new_field_name: email, "Email Error": email_error}


def merge_all_lists(old_field_name: str, new_field_name: str, records: list[dict]):
    all_items = set()
    for r in records:
        all_items.update(r.get(old_field_name, []))
    return {new_field_name: list(all_items)}


def merge_roof_accessible(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    tag = "Tengo acceso de mi techo / Roof access in my building"

    return {new_field_name: any([tag in r.get(old_field_name, []) for r in records])}


def merge_case_notes(old_field_name: str, new_field_name: str, records: list[dict]):
    return {
        new_field_name: "\n-------\n".join(
            [r.get(old_field_name, "").strip() for r in records if r.get(old_field_name)]
        )
    }


def merge_airtable_urls(old_field_name: str, new_field_name: str, records: list[dict]):
    return {
        new_field_name: "\n\n".join(
            [at_og.get_assistance_request_link(r[old_field_name]) for r in records]
        )
    }


def merge_open_requests(old_field_name: str, new_field_name: str, records: list[dict]):
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
            "items_output_field": "Social Services Requests",
            "request_type_output_field": None,
        },
    ]

    # get the unique set of all items
    all_items = list(set([item for r in records for item in r.get(old_field_name, [])]))

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
                if new_request_type not in output.get(request_type_output_field, []):
                    output[request_type_output_field].append(new_request_type)
                # remove the item from the top-level list
                if item in all_items_copy:
                    all_items_copy.remove(item)

            elif item in sub_items:
                # add the top-level request type if not already present
                if new_request_type and new_request_type not in output.get(
                    request_type_output_field, []
                ):
                    output[request_type_output_field].append(new_request_type)

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
    "Language": {"new_field": "Languages", "merge_fx": merge_all_lists},
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
        "merge_fx": select_first_non_null,
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
        "merge_fx": merge_all_lists,
    },
    "MESH - To confirm during outreach (before install)": {
        "new_field": "Roof Accessible?",
        "merge_fx": merge_roof_accessible,
    },
    "Case Notes": {"new_field": "General Notes", "merge_fx": merge_case_notes},
    "id": {"new_field": "Airtable URLs", "merge_fx": merge_airtable_urls},
    # Creates First Date Submitted and Last Date Submitted fields
    DATE_SUBMITTED_FIELD: {
        "new_field": DATE_SUBMITTED_FIELD,
        "merge_fx": merge_date_submitted,
    },
}


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
def get_open_records_for_households():
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
            merged_record.update(merge_fx(old_field_name, new_field_name, records))
        except Exception as e:
            raise Exception(f"Error merging {old_field_name} into {new_field_name}: {e}")
    return merged_record


def merge_households(households):
    output = []
    for records in households.values():
        output.append(merge_household_records(records))
    return output


def main():
    output = merge_households(get_open_records_for_households())
    df = pd.DataFrame(output)
    df.to_csv("households.csv", index=False)
    print(f"Wrote {len(output)} households to households.csv")


if __name__ == "__main__":
    main()
