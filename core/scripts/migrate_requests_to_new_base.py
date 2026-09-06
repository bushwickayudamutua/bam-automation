from urllib3 import Retry
import argparse
from collections import defaultdict
from typing import Tuple
import copy
import logging
import pandas as pd
from datetime import date, datetime
import numpy as np
import os
import sys

_CORE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _CORE_DIR not in sys.path:
    sys.path.insert(0, _CORE_DIR)

from bam_core.settings import AIRTABLE_BASE_ID, AIRTABLE_TOKEN, AIRTABLE_V2_BASE_ID
from bam_core.lib.airtable import Airtable
from bam_core.lib.airtable_v2 import (
    Household,
    MeshRequest,
    Request,
    FurnitureRequest,
    SocialServiceRequest,
)
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
    LOW_COST_INTERNET_AT_HOME_TYPE,
)

logging.basicConfig(level=logging.INFO, force=True)
log = logging.getLogger(__name__)

########################################
#  Setup Reference To OG Airtable Base #
########################################

at_og = Airtable(
    base_id=AIRTABLE_BASE_ID,
    token=AIRTABLE_TOKEN,
    retry_strategy=Retry(total=5, backoff_factor=1)
)
legacy_table = at_og.assistance_requests

#######################################
#  Fetch Open Requests Per Household  #
#######################################


def extract_open_requests_per_household(airtable_formula: str | None = None):
    """
    Get all open requests per household from digital ocean snapshots.
    :return: A dictionary of household records, where the key is the phone number
    and the value is a list of records for that household.
    """
    households = defaultdict(list)
    # get the last snapshot for each record
    for page in legacy_table.iterate(formula=airtable_formula):
        for record in page:
            analysis = Airtable.analyze_requests(record, include_all_mesh=True)

            open_requests = [
                req_type
                for sub_analysis in analysis.values()
                for req_type in sub_analysis["open"]
            ]
            if len(open_requests) <= 0: continue

            phone_number = format_phone_number(record[PHONE_FIELD])
            if not phone_number: continue

            # only add the household if there are open requests
            # and the phone number is valid
            households[phone_number].append({**record, "Open Requests": open_requests})
    return households


#######################################
#   Generic Transformation Functions  #
#######################################

def format_date(date_str: str) -> date | None:
    if not date_str or date_str == "":
        return None
    date_str = date_str.split("T")[0]
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def format_datetime(datetime_str: str) -> datetime | None:
    if not datetime_str or datetime_str == "":
        return None
    datetime_str = datetime_str.split(".")[0]
    return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S")


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
    first_date = min(dates) if dates else None
    last_date = max(dates) if dates else None

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


def transform_simple_lists(
    old_field_name: str, new_field_name: str, records: list[dict], return_set: bool=False
):
    return {new_field_name: [r.get(old_field_name) for r in records]}


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

    OTHER_LANGUAGE = "Otro / Other / 其他語言"
    LANGUAGE_MAPPING = {
        "Chino Toishanese / Toishanese / 台山话": "Chino Toishanés / Toishanese / 台山话",
        "Chino Cantonese / Cantonese / 广东话": "Chino Cantonés / Cantonese / 广东话",
        "Arabic / 阿拉伯語": "Árabe / Arabic / 阿拉伯語",
        "Portuguese / 葡萄牙語": "Portugués / Portuguese / 葡萄牙語",
        "Portuguese": "Portugués / Portuguese / 葡萄牙語",
        "Haitian Creole / French Creole / 法屬歸融語": "Criollo Haitiano / Haitian Creole / 法屬歸融語",
        "Otro / Other / 别的方言": OTHER_LANGUAGE,
    }

    output = transform_lists(old_field_name, new_field_name, records)
    # apply language mapping and deduplicate
    languages = list(set([
        LANGUAGE_MAPPING.get(item, item)
        for item in output[new_field_name]
    ]))
    if OTHER_LANGUAGE in languages:
        languages.remove(OTHER_LANGUAGE)
        languages.append(OTHER_LANGUAGE)
    output[new_field_name] = languages
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
        "Apartment": 2,
        "Building": 1,
        "No result": 0,
        "": 0,
        "Address Outside NY": -1,
        "Invalid Address Provided": -1,
    }
    ADDRESS_ACCURACY_MAP = {
        "": "No result"
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
    
    best_accuracy = records[best_idx].get("Cleaned Address Accuracy", "")

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
        "Address Accuracy": "No result" if best_accuracy == "" else best_accuracy,
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
        "Contacted about Mesh": 1,

        "Step 1 - Interested in Mesh": 2,
        "Interested in Mesh": 2,

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
        "Step 2 - LOS Confirmed": 7,
        "LOS Confirmed": 7,

        "Step 3 - Scheduling IN-PROGRESS": 8,
        "Scheduling IN-PROGRESS": 8,
        "Install in-progress": 8,
        "Install in-progress 2022": 8,
        "Step 5 - Install in-progress": 8,

        "Install Scheduled": 9,

        # Timed-out / ignore:
        "NYCHA - Currently Does Not Qualify": 10,
        "Cannot Install - Other Reason": 10,
        ">> MESH Cannot Install": 10,
        "Cannot Install - Does not have LOS": 10,
        "Does not have LOS": 10,
        "No LOS confirmed": 10,
        "Cannot Install - No Roof Access": 10,
        "No Roof Access": 10,
        "Not Interested": 10,
        "Cannot Install": 10,

        # Delivered:
        "YAY! MESH INSTALLED!": 11,
        "Mesh installed": 11,
        "Step 6 - Mesh installed": 11,
        
        # Needs repair (open):
        "INSTALL PENDING ELDERT REPAIR": 12,
    }
    OPEN_RANKS = list(range(10)) + [12]
    
    # pick the best non-closed MESH status:
    best_rank = -1
    unique_stats = set()
    mesh_history = ""
    for record in mesh_records:
        stat = record.get("MESH - Status", "")
        rank = MESH_PIPELINE_RANK.get(stat, -1)
        date_submitted = record.get(DATE_SUBMITTED_FIELD)
        if (stat not in ["", "Duplicate"]) and (stat not in unique_stats):
            unique_stats.add(stat)
            mesh_history += f"{date_submitted[0:10]}: {stat}\n"
        if rank > best_rank:
            best_rank = rank

    return (mesh_history, best_rank) if best_rank in OPEN_RANKS else (None, None)


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
        mesh_history, mesh_status_rank = get_best_mesh_status(bin_records)
        if mesh_status_rank is not None:
            mesh_dates = transform_date_submitted(DATE_SUBMITTED_FIELD, DATE_SUBMITTED_FIELD, bin_records)
            mesh_address = transform_address(bin_records)
            internet_access = transform_internet_access("Internet Access", "Internet Access", bin_records)
            mesh_requests.append({
                "Status": "Open",
                "MESH History": mesh_history,
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
        case_notes += f"[{date_submitted[0:10]}]({link})\n"
        notes = r.get(old_field_name)
        if notes:
            note_lines = "\n".join(
                [f"- {n.strip()}" for n in notes.split("\n") if n.strip()]
            )
            case_notes += note_lines
            case_notes += "\n"
        case_notes += "\n"
    
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

    # Map item labels:
    MAP_ITEMS = {
        "Platos / Plates / 盤子": "Platos o Tazas / Plates or Cups / 盘子或杯子",
        "Tazas / Cups / 杯子": "Platos o Tazas / Plates or Cups / 盘子或杯子",
    }

    all_items_df = [
        pd.DataFrame({
            "item": [item],
            DATE_SUBMITTED_FIELD: [(r.get(DATE_SUBMITTED_FIELD) or "")],
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
            .replace({"item": MAP_ITEMS})
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
        "id": {
            "new_field": "legacy_record_id",
            "transform_fx": transform_simple_lists,
        },
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

def create_eg_request_records(record: dict, household: Household) -> list[Request]:
    """
    Create Request instances from the transformed legacy assistance request record.
    :param record: The transformed household record
    :param household: The Household instance
    :return: List of Request instances
    """
    
    TYPES_TO_EXCLUDE = [
        "Muebles / Furniture / 家具",
        "Cosas de Cocina / Kitchen Supplies / 廚房用品",
        "Cama / Bed / 床",
    ]

    # combine the list of requests (no address information)
    all_reqs = pd.concat([
        record.get("Request Types", pd.DataFrame()),
        record.get("Kitchen Items", pd.DataFrame()),
    ], ignore_index=True)
    if all_reqs.shape[0] == 0:
        return []
    else:
        return [
            Request(
                household=household,
                type=req_type,
                status="Open",
                legacy_date_submitted=format_date(oldest_date),
                last_requested=format_datetime(latest_date),
            )
            for req_type, oldest_date, latest_date in zip(
                all_reqs["item"],
                all_reqs["Legacy First "+DATE_SUBMITTED_FIELD],
                all_reqs["Legacy Last "+DATE_SUBMITTED_FIELD],
            )
            if req_type not in TYPES_TO_EXCLUDE
        ]


def create_furniture_request_records(record: dict, household: Household) -> list[FurnitureRequest]:
    """
    Create FurnitureRequest instances from the transformed legacy assistance request record.
    :param record: The transformed household record
    :param household: The Household instance
    :return: List of FurnitureRequest instances
    """
    
    TYPES_TO_EXCLUDE = [
        "Muebles / Furniture / 家具",
        "Cosas de Cocina / Kitchen Supplies / 廚房用品",
        "Cama / Bed / 床",
    ]

    TYPE_MAP = {
        "Bastidor individual / Twin Bed Frame 單人床架" : "Bastidor individual / Twin Bed Frame / 單人床架",
    }

    # combine the list of requests (with geocode, and no other address information)
    all_reqs = pd.concat([
        record.get("Furniture Items", pd.DataFrame()),
        record.get("Bed Details", pd.DataFrame()),
    ], ignore_index=True)
    if all_reqs.shape[0] == 0:
        return []
    else:
        return [
            FurnitureRequest(
                household=household,
                type=TYPE_MAP.get(req_type, req_type),
                status="Open",
                legacy_date_submitted=format_date(oldest_date),
                last_requested=format_datetime(latest_date),
                geocode=record.get("Geocode"),
            )
            for req_type, oldest_date, latest_date in zip(
                all_reqs["item"],
                all_reqs["Legacy First "+DATE_SUBMITTED_FIELD],
                all_reqs["Legacy Last "+DATE_SUBMITTED_FIELD],
            )
            if req_type not in TYPES_TO_EXCLUDE
        ]


def create_ss_request_records(record: dict, household: Household) -> list[SocialServiceRequest]:
    """
    Create SocialServiceRequest instances from the transformed legacy assistance request record.
    :param record: The transformed household record
    :param household: The Household instance
    :return: List of SocialServiceRequest instances
    """
    
    TYPE_MAP = {
        "Asistencia para niños discapacitados / Assistance for disabled children / 殘疾兒童協助": "Asistencia para niños con discapacidad / Assistance for disabled children / 殘疾兒童協助",
        "Asistencia asegurando vivienda/ Securing housing / 住房協助": "Asistencia asegurando vivienda / Securing housing / 住房協助",
    }

    ss_reqs = record.get("Social Service Requests", pd.DataFrame())
    if ss_reqs.shape[0] == 0:
        return []
    else:
        return [
            SocialServiceRequest(
                household=household,
                type=TYPE_MAP.get(req_type, req_type),
                status="Open",
                legacy_date_submitted=format_date(oldest_date),
                last_requested=format_datetime(latest_date),
            )
            for req_type, oldest_date, latest_date in zip(
                ss_reqs["item"],
                ss_reqs["Legacy First "+DATE_SUBMITTED_FIELD],
                ss_reqs["Legacy Last "+DATE_SUBMITTED_FIELD],
            )
            if req_type != LOW_COST_INTERNET_AT_HOME_TYPE
        ]


def create_mesh_request_records(record: dict, household: Household) -> list[MeshRequest]:
    """
    Create MeshRequest instances from the transformed legacy assistance request record.
    :param record: The transformed household record
    :param household: The Household instance
    :return: List of MeshRequest instances
    """
    mesh_reqs = record.get("MESH Requests", [])
    if len(mesh_reqs) == 0:
        return []
    else:
        return [
            MeshRequest(
                household=household,
                status=r.get("Status"),
                mesh_history=r.get("MESH History"),
                legacy_date_submitted=format_date(r.get("Legacy First "+DATE_SUBMITTED_FIELD)),
                last_requested=format_datetime(r.get("Legacy Last "+DATE_SUBMITTED_FIELD)),
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


def create_household_record(record: dict) -> Household:
    """
    Create a Household instance from the transformed legacy assistance request record.
    :param record: The legacy assistance request record
    :return: The Household instance
    """
    return Household(
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
        "--subset_case_num",
        type=str,
        default=None,
        help="Selected Case #s to migrate from the legacy requests",
    )
    parser.add_argument(
        "--subset_formula",
        type=str,
        default=None,
        help="Formula to select records to migrate from the legacy requests",
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
    
    legacy_requests = extract_open_requests_per_household(args.subset_formula)  

    n_numbers = len(legacy_requests)
    if n_numbers == 0:
        log.error("Found no open legacy requests!")
        return

    log.info("Extracted %s legacy households!", n_numbers)

    if args.output_dir:
        output_path = os.path.join(args.output_dir, "legacy_households.txt")
        with open(output_path, "w") as f:
            for line_str in legacy_requests.keys():
                f.write(f"{line_str}\n")

    if args.subset_case_num:
        with open(args.subset_case_num, "r") as f:
            selected_case_nums = {int(line_str.strip()) for line_str in f.read().splitlines()}
            legacy_requests = {
                num: filtered_requests
                for num, requests in legacy_requests.items()
                if (filtered_requests := [req for req in requests if req['Case #'] in selected_case_nums])
            }
            n_numbers = len(legacy_requests)
            if n_numbers == 0:
                log.error("No records to transform after subsetting to '%s'", args.subset_case_num)
                return
            log.info("Subsetting to %s households from '%s'", n_numbers, args.subset_case_num)

    log.info("Starting transformation for %s phone numbers!", n_numbers)
    transformed_requests = transform_households(legacy_requests)

    n_records = len(transformed_requests)
    if n_records == 0:
        log.error("No transformed requests to migrate!")
        return
    log.info("Transformed %s records!", n_records)

    if args.output_dir:
        output_path = os.path.join(args.output_dir, "transformed_households.txt")
        with open(output_path, "w") as f:
            for r in transformed_requests:
                line_str = r.get(PHONE_FIELD)
                f.write(f"{line_str}\n")
    
    if args.transform_only:
        log.info("Skipping migration!")
        return

    log.info("Generating new records.")
    households: list[Household] = []

    requests: list[Request] = []
    furniture_requests: list[FurnitureRequest] = []
    ss_requests: list[SocialServiceRequest] = []
    mesh_requests: list[MeshRequest] = []

    legacy_record_map: dict[str, Tuple[str, Household]] = {}
    for record in transformed_requests:
        household = create_household_record(record)
        households.append(household)

        requests.extend(create_eg_request_records(record, household))
        furniture_requests.extend(create_furniture_request_records(record, household))
        ss_requests.extend(create_ss_request_records(record, household))
        mesh_requests.extend(create_mesh_request_records(record, household))

        migration_date = datetime.now().strftime("%m/%d/%Y %H:%M")
        for lid in record.get("legacy_record_id", []):
            legacy_record_map[lid] = (migration_date, household)

    log.info(
        "Generated %s households, %s EG requests, %s furniture requests, %s social service requests, and %s mesh requests from %s legacy records.",
        len(households),
        len(requests),
        len(furniture_requests),
        len(ss_requests),
        len(mesh_requests),
        len(legacy_record_map)
    )

    log.info("Migrating all records.")
    # Households need to be saved first so that other records can refer to their IDs
    Household.batch_save(households)

    Request.batch_save(requests)
    FurnitureRequest.batch_save(furniture_requests)
    SocialServiceRequest.batch_save(ss_requests)
    MeshRequest.batch_save(mesh_requests)

    HOUSEHOLD_URL_PREFIX = f"https://airtable.com/{AIRTABLE_V2_BASE_ID}/{Household.meta.table.id}"
    legacy_table.batch_update([
        {"id": lid, "fields": {
            "Migration Date": migration_date, 
            "New Household": f"[{household.name}]({HOUSEHOLD_URL_PREFIX}/{household.id})",
        }}
        for lid, (migration_date, household) in legacy_record_map.items()
    ])

    log.info("Migration completed successfully!")


if __name__ == "__main__":
    main()
