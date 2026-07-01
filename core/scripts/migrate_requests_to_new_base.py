import argparse
from collections import defaultdict
import copy
import logging
import pandas as pd
from datetime import date, datetime
import numpy as np
import os
import sys

# Allow running as `python scripts/migrate_requests_to_new_base.py` without `pip install -e ./core`
_CORE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _CORE_DIR not in sys.path:
    sys.path.insert(0, _CORE_DIR)

from bam_core.settings import AIRTABLE_BASE_ID, AIRTABLE_TOKEN
from bam_core.lib.airtable import Airtable
from bam_core.lib.airtable_v2 import (
    Household,
    MeshRequest,
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
    LOW_COST_INTERNET_AT_HOME_TYPE,
)

log = logging.getLogger(__name__)


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
        open_requests = afr.get_open_requests_for_snapshot(
            record_id, snapshot, include_all_mesh=True
        )

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

def format_date(date_str: str) -> date | None:
    if not date_str or date_str == "":
        return None
    return datetime.strptime(date_str, "%Y-%m-%d").date()


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


def convert_str_to_int(num_str, num_digits=np.inf):
    num_str = "".join([c for c in str(num_str).strip() if c.isdigit()])
    
    if len(num_str) > num_digits:
        num_str = num_str[:num_digits]

    try:
        return int(num_str) 
    except (ValueError, KeyError):
        return None


############################################
#  Field-Specific Transformation Functions #
############################################

def transform_last_texted(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    """
    Get most recent date they were texted for outreach.
    """
    dates = [r.get(old_field_name) for r in records]
    dates = [d for d in dates if d and d != ""]
    last_date = max(dates) if dates else None
    return { new_field_name: last_date }


def transform_date_submitted(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    """
    Create two new fields: "Legacy First Date Submitted" and "Legacy Last Date Submitted"
    representing the first and last date a request was submitted for the household.
    """
    
    dates = [r.get(old_field_name) for r in records]
    dates = [d for d in dates if d and d != ""]
    first_date = min(dates).split("T")[0] if dates else None
    last_date = max(dates).split("T")[0] if dates else None

    return {
        f"Legacy First {new_field_name}": first_date,
        f"Legacy Last {new_field_name}": last_date,
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
    old_field_name: str, new_field_name: str, records: list[dict], return_set: bool=False
):
    """
    Given a list of records, merge all the values of the old field into a single list
    and remove duplicates.
    """
    all_items = set()
    for r in records:
        all_items.update(r.get(old_field_name) or [])
    
    if return_set:
        return {new_field_name: all_items}
    else:
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


def transform_other_languages(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    """
    Concatenate all "other" languages into a single line text.
    """
    other_languages = [(r.get(old_field_name) or "").strip() for r in records]
    other_languages = [l for l in set(other_languages) if l != ""]
    other_languages = "\n".join(other_languages) if len(other_languages) > 0 else None
    return { new_field_name: other_languages }


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


def transform_address(records: list[dict]):

    ADDRESS_PIPELINE_RANK = {
        "Apartment": 3,
        "Building": 2,
        "Address Outside NY": 1,
        "No result": 0,
        "": 0,
        "Invalid Address Provided": -1,
    }

    best_idx_rank = np.argmax([
        ADDRESS_PIPELINE_RANK.get(r.get("Cleaned Address Accuracy", ""), -2)
        for r in records
    ])
    best_idx = best_idx_rank

    address = records[best_idx].get("Cleaned Address", "").strip()
    street_address = records[best_idx].get("Current Address", "").strip()
    if address == "" and street_address == "":
        best_idx = [
            i for i in range(len(records))
            if records[i].get("Cleaned Address", "").strip() != ""
        ]
        if len(best_idx) > 0:
            best_idx = best_idx[0]
        else:
            best_idx = [
                i for i in range(len(records))
                if records[i].get("Current Address", "").strip() != ""
            ]
            if len(best_idx) > 0:
                best_idx = best_idx[0]
            else:
                best_idx = best_idx_rank
    
    best_accuracy = records[best_idx].get("Cleaned Address Accuracy")

    address = records[best_idx].get("Cleaned Address", "").strip()
    street_address = records[best_idx].get("Current Address", "").strip()
    city_state = records[best_idx].get("Current Address - City, State", "").strip()
    zip_code = records[best_idx].get("Current Address - Zip Code", "").strip()
    if address == "":
        address = (street_address + ' ' + city_state + ' ' + zip_code).strip()
    
    address = None if address == "" else address
    street_address = None if street_address == "" else street_address
    city_state = None if city_state == "" else city_state
    zip_code = convert_str_to_int(zip_code, num_digits=5)

    return {
        "Address Accuracy": best_accuracy,
        "Address": address,
        "Street Address": street_address,
        "City, State": city_state,
        "Zip Code": zip_code,
    }


def get_best_mesh_status(mesh_records: list[dict]) -> tuple[str | None, int | None]:
    """Best non-closed MESH - Status for a household (unique phone & BIN)."""

    # MESH status pipeline (higher --> further along).
    MESH_PIPELINE_RANK = {
        # Empty (open):
        "": 0,
        "Duplicate": 0,
        "Node Building": 0,
        "Step 2.6 (optional) Node Building": 0,
        
        # In-progress (open):
        "Texted about Mesh": 1,

        "Step 1 - Interested in Mesh": 2,

        "Needs Panorama": 3,
        "Step 2.5 (optional) - Needs Panorama": 3,

        "Roof Access In Process": 4,

        "Confirming Premission with Landlord": 5,

        "Roof Access Confirmed": 6,
        "Step 4 - Roof Access Confirmed": 6,

        "Step 2- LOS Confirmed": 7,
        "Step 2 - LOS Tool Confirmed": 7,
        "LOS confirmed": 7,
        "LOS confirmed - Update this": 7,
        "LOS Tool Confirmed": 7,
        "Step 3 - LOS Confirmed": 7,

        "Step 3 - Scheduling IN-PROGRESS": 8,
        "Install in-progress": 8,
        "Install in-progress 2022": 8,
        "Step 5 - Install in-progress": 8,

        "Install Scheduled": 9,

        # Delivered:
        "YAY! MESH INSTALLED!": 10,
        "Mesh installed": 10,
        "Step 6 - Mesh installed": 10,

        # Closed / ignore:
        "NYCHA - Currently Does Not Qualify": 11,
        "Cannot Install - Other Reason": 11,
        ">> MESH Cannot Install": 11,
        "Cannot Install - Does not have LOS": 11,
        "Does not have LOS": 11,
        "No LOS confirmed": 11,
        "Cannot Install - No Roof Access": 11,
        "No Roof Access": 11,
        "Not Interested": 11,
        
        # Needs repair (open):
        "INSTALL PENDING ELDERT REPAIR": 12,
    }
    OPEN_RANKS = list(range(10)) + [12]
    MESH_STATUS_OLD_TO_NEW = {
        "": "Open",
        "Duplicate": "Open",
        "Node Building": "Open",
        "Step 2.6 (optional) Node Building": "Open",

        "Needs Panorama": "Needs Panorama",
        "Step 2.5 (optional) - Needs Panorama": "Needs Panorama",

        "Confirming Premission with Landlord": "Confirming Permission with Landlord",

        "Step 4 - Roof Access Confirmed": "Roof Access Confirmed",

        "Step 2- LOS Confirmed": "Step 2 - LOS Confirmed",
        "Step 2 - LOS Tool Confirmed": "Step 2 - LOS Confirmed",
        "LOS confirmed": "Step 2 - LOS Confirmed",
        "LOS confirmed - Update this": "Step 2 - LOS Confirmed",
        "LOS Tool Confirmed": "Step 2 - LOS Confirmed",
        "Step 3 - LOS Confirmed": "Step 2 - LOS Confirmed",
        
        "Install in-progress": "Step 3 - Scheduling IN-PROGRESS",
        "Install in-progress 2022": "Step 3 - Scheduling IN-PROGRESS",
        "Step 5 - Install in-progress": "Step 3 - Scheduling IN-PROGRESS",
        
        "Mesh installed": "YAY! MESH INSTALLED!",
        "Step 6 - Mesh installed": "YAY! MESH INSTALLED!",
        
        "Does not have LOS": "Cannot Install - Does not have LOS",
        "No LOS confirmed": "Cannot Install - Does not have LOS",
        "No Roof Access": "Cannot Install - No Roof Access",
        ">> MESH Cannot Install": "Cannot Install - Other Reason",
    }
    
    # pick the best non-closed MESH status:
    best_stat = None
    best_rank = -1
    for record in mesh_records:
        stat = record.get("MESH - Status", "")
        rank = MESH_PIPELINE_RANK.get(stat, -1)
        log.debug("MESH Status: '%s', Rank: %s", stat, rank)
        if rank > best_rank:
            best_stat = MESH_STATUS_OLD_TO_NEW.get(stat, stat)
            best_rank = rank
            log.debug("Best MESH Status: '%s', Best Rank: %s", best_stat, best_rank)

    return (best_stat, best_rank) if best_rank in OPEN_RANKS else (None, None)


def transform_mesh_requests(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    """
    Find the best MESH status (latest in the pipeline) for each household (unique phone & BIN).
    """
    mesh_per_bin = defaultdict(list)
    for record in records:
        if LOW_COST_INTERNET_AT_HOME_TYPE in (record.get("Open Requests") or []):
            bin_val = record.get("Building Identification Number", "")
            mesh_per_bin[bin_val].append(record)

    mesh_requests = []
    for bin_val, bin_records in mesh_per_bin.items():
        log.debug("BIN: '%s', Phone: '%s'", bin_val, bin_records[0].get(PHONE_FIELD))
        mesh_status, mesh_status_rank = get_best_mesh_status(bin_records)
        if mesh_status:
            mesh_dates = transform_date_submitted(DATE_SUBMITTED_FIELD, DATE_SUBMITTED_FIELD, bin_records)
            mesh_address = transform_address(bin_records)
            internet_access = transform_internet_access("Internet Access", "Internet Access", bin_records)
            mesh_requests.append({
                "Status": mesh_status,
                "Building Identification Number": convert_str_to_int(bin_val),
                **mesh_dates,
                **mesh_address,
                **internet_access,
            })

    return {"MESH Requests": mesh_requests} if mesh_requests else {}


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


def transform_cita_availability(
    old_field_name: str, new_field_name: str, records: list[dict]
):
    """
    Create new boolean fields "Needs Delivery" and "Needs Email Outreach" based on the old field "Cita Availability"
    """
    output = transform_lists(old_field_name, old_field_name, records, return_set=True)
    return {
        "Needs Delivery": "Needs Delivery" in output[old_field_name],
        "Needs Email Outreach": "Needs Email Outreach" in output[old_field_name],
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
    # NOT excluding these social service types for now.
        # "Asistencia legal de inquilinos / Tenant legal assistance / 租戶法律協助",
        # "Asistencia con servicios escolares / Assistance with in-school services / 學校服務協助",
        # "Asistencia asegurando vivienda/ Securing housing / 住房協助",
        # "Asistencia con seguro médico / Medical insurance support / 醫療保險協助",
        # "Asistencia de Negocios / Small Business Support / 小型企業協助",
        # "Asistencia con beneficios de comida / Assistance with food benefits / 食品福利協助（WIC, SNAP, P-EBT）",
        # "Asistencia con Transporte / Transportation Assistance / 交通運輸協助",
        # "Asistencia para mascotas / Pet Assistance / 寵物協助",
    # Excluding these types from migration:
        "Asistencia legal de inmigración / Immigration legal assistance / 移民法律協助",
        "Comida de mascota / Pet Food / 寵物食品",
        "Alimentos / Groceries / 食品",
        "Comida caliente / Hot meals / 热食",
        "Otras / Other / 其他家具",
        "Otras / Other / 其他廚房用品",
        LOW_COST_INTERNET_AT_HOME_TYPE, # MESH Requests handled separately
    ]

    all_items_df = [
        pd.DataFrame({
            "item": [item],
            DATE_SUBMITTED_FIELD: [(r.get(DATE_SUBMITTED_FIELD) or "").split("T")[0]],
        })
        for r in records for item in (r.get(old_field_name) or [])
    ]
    all_items_df = pd.concat(all_items_df or [pd.DataFrame()], ignore_index=True)

    # filter out items we aren't migrating and "Historical" items
    not_historical = pd.Series(["historical" not in item.lower() for item in all_items_df.get("item",[])])
    not_excluded_item = ~all_items_df.get("item",[]).isin(EXCLUDE_ITEMS)
    keep_idx = not_historical & not_excluded_item
    all_items_df = all_items_df[keep_idx]

    output = defaultdict(pd.DataFrame)
    # first check for sub-items and remove them from the top-level list
    for sub_item in REQUEST_SUB_ITEMS:
        # unpack sub_item
        new_request_type = sub_item["new_request_type"]
        old_request_type = sub_item["old_request_type"]
        sub_items = sub_item["items"]
        items_output_field = sub_item["items_output_field"]
        request_type_output_field = sub_item["request_type_output_field"]
        
        # merge top-level request type
        if old_request_type:
            old_type_idx = all_items_df["item"] == old_request_type
            if old_type_idx.any():
                if new_request_type:
                    new_item_df = all_items_df[old_type_idx].copy()
                    new_item_df["item"] = new_request_type
                    output[request_type_output_field] = pd.concat([output[request_type_output_field], new_item_df])
                # remove the item from the top-level list
                all_items_df = all_items_df[~old_type_idx]
        
        sub_item_idx = all_items_df["item"].isin(sub_items)
        if sub_item_idx.any():
            # add the top-level request type if not already present
            if new_request_type:
                new_item_df = all_items_df[sub_item_idx].copy()
                new_item_df["item"] = new_request_type
                output[request_type_output_field] = pd.concat([output[request_type_output_field], new_item_df])
            
            # add the item to the output list
            new_item_df = all_items_df[sub_item_idx].copy()
            output[items_output_field] = pd.concat([output[items_output_field], new_item_df])
            # remove the item from the top-level list
            all_items_df = all_items_df[~sub_item_idx]
    
    # add any remaining items to the top-level list
    output[new_field_name] = pd.concat([output[new_field_name], all_items_df])
    
    # de-dupe requests of each type (keep oldest and latest dates):
    output = {
        name: (
            item_df
            .groupby("item")[DATE_SUBMITTED_FIELD]
            .agg(["min", "max"])
            .reset_index()
            .rename(
                columns={
                    "min": "Legacy First "+DATE_SUBMITTED_FIELD,
                    "max": "Legacy Last "+DATE_SUBMITTED_FIELD,
                }
            )
        )
        for name, item_df in output.items()
    }
    
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
        PHONE_FIELD: {
            "new_field": PHONE_FIELD,
            "transform_fx": select_first
        },
        "Invalid Phone Number?": {
            "new_field": "Invalid Phone Number?",
            "transform_fx": transform_invalid_phone_number,
        },
        "Intl Phone Number?": {
            "new_field": "Int'l Phone Number?",
            "transform_fx": transform_intl_phone_number,
        },
        # Includes both Email and Email Error
        "Email": {
            "new_field": "Email",
            "transform_fx": transform_email
        },
        "Language": {
            "new_field": "Languages",
            "transform_fx": transform_languages,
        },
        "What Languages?": {
            "new_field": "Other Languages",
            "transform_fx": transform_other_languages,
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
        # Includes boolean fields "Needs Delivery" and "Needs Email Outreach"
        "Cita Availability": {
            "new_field": "",
            "transform_fx": transform_cita_availability,
        },
        "Open Requests": { # Requests per Phone (everything except MESH Requests):
            "new_field": "Request Types",
            "transform_fx": transform_open_requests,
        },
        "MESH": { # MESH Requests per Phone+BIN:
            "new_field": "MESH Requests",
            "transform_fx": transform_mesh_requests
        },
        "Geocode": {
            "new_field": "Geocode",
            "transform_fx": select_first_non_null,
        },
        "Last Auto Texted": {
            "new_field": "Last Texted",
            "transform_fx": transform_last_texted,
        },
        "Furniture Acknowledgement": {
            "new_field": "Furniture Acknowledgement",
            "transform_fx": set_true,
        },
    }

    # sort records by Date Submitted (order from most recent to oldest)
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
def create_requests_records(record: dict, household: Household):
    """
    Create Requests rows from the transformed legacy assistance request record.
    :param record: The transformed household record
    :param household: The saved Household instance
    :return: List of Request instances (empty if none to create)
    """
    
    TYPES_TO_EXCLUDE = [
        "Muebles / Furniture / 家具",
        "Cosas de Cocina / Kitchen Supplies / 廚房用品",
        "Cama / Bed / 床",
    ]

    TYPE_MAP = {
        "Bastidor individual / Twin Bed Frame 單人床架" : "Bastidor individual / Twin Bed Frame / 單人床架",
    }

    # combine the list of requests (no address information)
    all_reqs1 = pd.concat([
        record.get("Request Types", pd.DataFrame()),
        record.get("Kitchen Items", pd.DataFrame()),
    ], ignore_index=True)
    request_records1 = []
    if all_reqs1.shape[0] > 0:
        request_records1 = [
            Request(
                household=household,
                type=TYPE_MAP.get(req_type, req_type),
                status="Open",
                legacy_date_submitted=format_date(oldest_date),
                last_requested=format_date(latest_date),
            )
            for req_type, oldest_date, latest_date in zip(
                all_reqs1["item"],
                all_reqs1["Legacy First "+DATE_SUBMITTED_FIELD],
                all_reqs1["Legacy Last "+DATE_SUBMITTED_FIELD],
            )
            if req_type not in TYPES_TO_EXCLUDE
        ]

    # combine the list of requests (with geocode, and no other address information)
    all_reqs2 = pd.concat([
        record.get("Furniture Items", pd.DataFrame()),
        record.get("Bed Details", pd.DataFrame()),
    ], ignore_index=True)
    request_records2 = []
    if all_reqs2.shape[0] > 0:
        request_records2 = [
            Request(
                household=household,
                type=TYPE_MAP.get(req_type, req_type),
                status="Open",
                legacy_date_submitted=format_date(oldest_date),
                last_requested=format_date(latest_date),
                geocode=record.get("Geocode"),
            )
            for req_type, oldest_date, latest_date in zip(
                all_reqs2["item"],
                all_reqs2["Legacy First "+DATE_SUBMITTED_FIELD],
                all_reqs2["Legacy Last "+DATE_SUBMITTED_FIELD],
            )
            if req_type not in TYPES_TO_EXCLUDE
        ]

    request_records = request_records1 + request_records2
    if request_records:
        Request.batch_save(request_records)
    return request_records


@retry(attempts=5, wait=1, backoff=2)
def create_ss_requests_records(record: dict, household: Household):
    """
    Create Social Service Requests rows from the transformed legacy assistance request record.
    :param record: The transformed household record
    :param household: The saved Household instance
    :return: List of SocialServiceRequest instances (empty if none to create)
    """
    
    TYPE_MAP = {
        "Asistencia para niños discapacitados / Assistance for disabled children / 殘疾兒童協助": "Asistencia para niños con discapacidad / Assistance for disabled children / 殘疾兒童協助",
        "Asistencia asegurando vivienda/ Securing housing / 住房協助": "Asistencia asegurando vivienda / Securing housing / 住房協助",
    }

    ss_reqs = record.get("Social Service Requests", pd.DataFrame())
    ss_records = []
    if ss_reqs.shape[0] > 0:
        ss_records = [
            SocialServiceRequest(
                household=household,
                type=TYPE_MAP.get(req_type, req_type),
                status="Open",
                legacy_date_submitted=format_date(oldest_date),
                last_requested=format_date(latest_date),
            )
            for req_type, oldest_date, latest_date in zip(
                ss_reqs["item"],
                ss_reqs["Legacy First "+DATE_SUBMITTED_FIELD],
                ss_reqs["Legacy Last "+DATE_SUBMITTED_FIELD],
            )
            if req_type != LOW_COST_INTERNET_AT_HOME_TYPE
        ]

    if ss_records:
        SocialServiceRequest.batch_save(ss_records)
    return ss_records


@retry(attempts=5, wait=1, backoff=2)
def create_mesh_requests_records(record: dict, household: Household):
    """
    Create Mesh Requests rows from the transformed legacy assistance request record.
    :param record: The transformed household record
    :param household: The saved Household instance
    :return: List of MeshRequest instances (empty if none to create)
    """
    mesh_reqs = record.get("MESH Requests", [])
    mesh_records = []
    if mesh_reqs:
        mesh_records = [
            MeshRequest(
                household=household,
                status=r.get("Status"),
                legacy_date_submitted=format_date(r.get("Legacy First "+DATE_SUBMITTED_FIELD)),
                last_requested=format_date(r.get("Legacy Last "+DATE_SUBMITTED_FIELD)),
                internet_access=r.get("Internet Access") or [],
                address_accuracy=r.get("Address Accuracy"),
                address=r.get("Address"),
                street_address=r.get("Street Address"),
                city_and_state=r.get("City, State"),
                zip_code=r.get("Zip Code"),
                building_identification_number=r.get("Building Identification Number"),
            )
            for r in mesh_reqs
        ]

    if mesh_records:
        MeshRequest.batch_save(mesh_records)
    return mesh_records


@retry(attempts=5, wait=1, backoff=2)
def create_household_record(record: dict):
    """
    Create a household record from the transformed legacy assistance request record.
    :param record: The legacy assistance request record
    :return: The created Household instance
    """
    household = Household(
        name=record.get("Name"),
        phone_number=record.get(PHONE_FIELD),
        phone_is_invalid=record.get("Invalid Phone Number?"),
        phone_is_intl=record.get("Int'l Phone Number?"),
        email=record.get("Email"),
        email_error=record.get("Email Error"),
        legacy_first_date_submitted=format_date(record.get("Legacy First "+DATE_SUBMITTED_FIELD)),
        legacy_last_date_submitted=format_date(record.get("Legacy Last "+DATE_SUBMITTED_FIELD)),
        languages=record.get("Languages"),
        other_languages=record.get("Other Languages"),
        notes=record.get("Notes"),
        last_texted=format_date(record.get("Last Texted")),
        last_called=None,
        needs_delivery=record.get("Needs Delivery"),
        needs_email_outreach=record.get("Needs Email Outreach"),
    )
    household.save()
    return household


def load_household(record: dict):
    """
    Migrate an assistance request from the old base to the new base,
    creating records in all the necessary tables.
    :param record: The legacy assistance request record
    :return: None
    """
    household = create_household_record(record)
    create_requests_records(record, household)
    create_ss_requests_records(record, household)
    create_mesh_requests_records(record, household)


#######################################
#   Helper Functions for Testing     #
#######################################

def _has_mesh_requests(record: dict):
    mesh_reqs = record.get("MESH Requests", [])
    return len(mesh_reqs) > 0


#######################################
#   CLI                               #
#######################################


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="""
            Migrate requests from old base to new base. MAKE SURE YOU HAVE YOUR .env FILE SET UP CORRECTLY.
        """
    )
    parser.add_argument(
        "--transform_only",
        action="store_true",
        help="Transform records without migrating to new base",
    )
    parser.add_argument(
        "--subset",
        type=str,
        default=None,
        help="Selected phone numbers to migrate from the legacy requests",
    )
    parser.add_argument(
        "--subset_func",
        type=str,
        default=None,
        help="Function to select phone numbers to migrate from the legacy requests",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default=None,
        help="Path to output directory",
    )
    args = parser.parse_args()

    if args.output_dir:
        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir)
    
    legacy_requests = extract_open_requests_per_household()  

    n_numbers = len(legacy_requests)
    if n_numbers == 0:
        log.warning("Found no open legacy requests!")
        return

    log.info("Extracted %s legacy households!", n_numbers)

    if args.output_dir:
        output_path = os.path.join(args.output_dir, "legacy_households.txt")
        with open(output_path, "w") as f:
            for line_str in legacy_requests.keys():
                f.write(f"{line_str}\n")

    if args.subset:
        with open(args.subset, "r") as f:
            subset_str = [line_str.strip() for line_str in f.read().splitlines()]
            selected_numbers = {num for num_str in subset_str if (num := format_phone_number(num_str))}
            legacy_requests = {
                num: requests
                for num, requests in legacy_requests.items()
                if num in selected_numbers
            }
            n_numbers = len(legacy_requests)
            if n_numbers == 0:
                log.warning("No records to transform after subsetting to '%s'", args.subset)
                return
            log.info("Subsetting to %s households from '%s'", n_numbers, args.subset)
            n_missing = len(subset_str) - n_numbers
            if n_missing > 0:
                log.warning("Missing %s of provided phone numbers!", n_missing)

    log.info("Starting transformation for %s phone numbers!", n_numbers)
    transformed_requests = transform_households(legacy_requests)

    n_records = len(transformed_requests)
    if n_records == 0:
        log.warning("No transformed requests to migrate!")
        return
    log.info("Transformed %s records!", n_records)

    if args.subset_func:
        subset_func = globals().get(args.subset_func)
        if subset_func is not None and callable(subset_func):
            transformed_requests = [r for r in transformed_requests if subset_func(r)]
            n_records = len(transformed_requests)
            if n_records == 0:
                log.warning("No records to migrate after subsetting with %s", args.subset_func)
                return
            log.info("Selected %s households with %s", n_records, args.subset_func)
        else:
            log.error("Function %s not found or not callable!", args.subset_func)
            return

    if args.output_dir:
        output_path = os.path.join(args.output_dir, "transformed_households.txt")
        with open(output_path, "w") as f:
            for r in transformed_requests:
                line_str = r.get(PHONE_FIELD)
                f.write(f"{line_str}\n")
    
    if args.transform_only:
        log.info("Skipping migration!")
        return

    log.info("Starting migration of %s records.", n_records)
    for i, household_request in enumerate(transformed_requests):
        if i % 100 == 0:
            log.info("Migrated %s records. %s records left.", i, n_records - i)
        try:
            load_household(household_request)
            if i == n_records - 1:
                log.info("Migrated %s records.", i + 1)
        except Exception:
            log.error("Failed at %s for %s", i + 1, household_request.get(PHONE_FIELD))
            raise

    log.info("Migration completed successfully!")


if __name__ == "__main__":
    main()

