# Changes:
# - no new line at the end
# - move filters to functions
# - log all filters
# - fix skipping?! (skips item instead of just language)

import pandas as pd
import numpy as np
from pyairtable import Api
from pyairtable.formulas import *
from bam_core.constants import *
from datetime import datetime
import dotenv
import os
import yaml

# Essential Goods table:
dotenv.load_dotenv()
BAM_AIRTABLE_TOKEN = os.getenv("BAM_AIRTABLE_TOKEN", None)
BAM_AIRTABLE_BASE_ID = os.getenv("BAM_AIRTABLE_BASE_ID", None)
BAM_AIRTABLE_ASSISTANCE_REQUESTS_TABLE_ID = os.getenv("BAM_AIRTABLE_ASSISTANCE_REQUESTS_TABLE_ID", None)
api = Api(BAM_AIRTABLE_TOKEN)
table = api.table(BAM_AIRTABLE_BASE_ID, BAM_AIRTABLE_ASSISTANCE_REQUESTS_TABLE_ID)

# Input parameters:
os.chdir("/Users/personal/git/bam-automation/core/bam_core/functions/outreach/")
with open("outreach_params.yaml") as f:
    params = yaml.safe_load(f)

# Logging:
import logging
os.mkdir(params["output"])
log_file = os.path.join(params["output"], "outreach_airtable.log")
logging.basicConfig(filename=log_file, format='%(asctime)s %(message)s', filemode='w')
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# No limit by default:
if "total_capacity" not in params:
    params["total_capacity"] = np.inf

# Conditions applying to all:
conditions_init = [
    EQ(Field(INVALID_NUMBER_FIELD), False), # filter out invalid phone numbers
    OR( # filtering by expected eg distro date (always include empty fields)
        EQ(Field(EXPECTED_EG_DATE_FIELD), ""),
        Formula(params["eg_distro_date"])
    ),
    OR( # filtering by last auto texted date (always include empty fields)
        EQ(Field(LAST_TEXTED_DATE_FIELD), ""),
        Formula(params["auto_texted_date"])
    ),
]
conditions_init = conditions_init + [Formula(formula_str) for formula_str in params["filter_other"]] # custom filters with pyairtable format

if "exclude_numbers" in params:
    exclude = pd.read_csv(params["exclude_numbers"])["Phone Number"]
else:
    exclude = []

i = 0
phone_numbers_all = pd.Series()
# Loop through eg items in order of priority:
for item in params["items"]:
    phone_numbers_item = pd.Series()
    # Check if we've reached total capacity:
    if len(phone_numbers_all) >= params["total_capacity"]:
        logger.warning("Reached total capacity! Skipping "+item["name"])
        break
    # Find open requests for this eg item (or kitchen items):
    conditions_item = []
    if "EG_item" in item:
        for item_name in item["EG_item"]:
            item_delivered = EG_REQUESTS_SCHEMA["items"][item_name]["delivered"]
            item_timeout = EG_REQUESTS_SCHEMA["items"][item_name]["timeout"]
            conditions_item.append(FIND(item_name, Field(EG_REQUESTS_FIELD)))
            conditions_item.append(NOT(FIND(item_delivered, Field(EG_STATUS_FIELD))))
            conditions_item.append(NOT(FIND(item_timeout, Field(EG_STATUS_FIELD))))
    if "kitchen_items" in item:
        for item_name in item["kitchen_items"]:
            item_delivered = KITCHEN_REQUESTS_SCHEMA["items"][item_name]["delivered"]
            item_timeout = KITCHEN_REQUESTS_SCHEMA["items"][item_name]["timeout"]
            conditions_item.append(FIND(item_name, Field(KITCHEN_REQUESTS_FIELD)))
            conditions_item.append(NOT(FIND(item_delivered, Field(EG_STATUS_FIELD))))
            conditions_item.append(NOT(FIND(item_timeout, Field(EG_STATUS_FIELD))))
        item_name = "Cosas de Cocina / Kitchen Supplies / 廚房用品"
        item_delivered = EG_REQUESTS_SCHEMA["items"][item_name]["delivered"]
        item_timeout = EG_REQUESTS_SCHEMA["items"][item_name]["timeout"]
        conditions_item.append(NOT(FIND(item_delivered, Field(EG_STATUS_FIELD))))
        conditions_item.append(NOT(FIND(item_timeout, Field(EG_STATUS_FIELD))))
    # Loop through languages in order of priority:
    for language in params["languages"]:
        # Check if we've reached capacity for this item (no limit by default):
        if ("capacity" in item) and (len(phone_numbers_item) >= item["capacity"]):
            logger.warning("Reached item capacity! Skipping "+item["name"]+";"+language)
            break
        # Check if we've reached total capacity:
        if len(phone_numbers_all) >= params["total_capacity"]: 
            logger.warning("Reached total capacity! Skipping "+item["name"]+";"+language)
            break
        # Find open requests with this language:
        if isinstance(VALID_LANGUAGES[language], list):
            conditions_language = []
            for language_name in VALID_LANGUAGES[language]:
                conditions_language.append(FIND(language_name, Field(LANGUAGE_FIELD)))
            conditions_language = OR(*conditions_language)
        else:
            language_name = VALID_LANGUAGES[language]
            conditions_language = FIND(language_name, Field(LANGUAGE_FIELD))
        # Apply all filters and collect records from AirTable:
        conditions_all = AND(*conditions_init, *conditions_item, conditions_language)
        sort = item["sort"] if ("sort" in item) else [DATE_SUBMITTED_FIELD]
        fields = ["Case #", PHONE_FIELD, FIRST_NAME_FIELD]
        if "view" in item:
            records = table.all(formula=conditions_all, sort=sort, fields=fields, view=item["view"])
        else:
            records = table.all(formula=conditions_all, sort=sort, fields=fields)
        if len(records) == 0:
            logger.warning("No requests found! Skipping "+item["name"]+";"+language)
            break
        records_df = pd.DataFrame([{"record_id": records[i]["id"], **records[i]["fields"]} for i in range(len(records))])
        # Remove duplicated phone numbers:
        rmv = records_df[PHONE_FIELD].duplicated() | records_df[PHONE_FIELD].isin(phone_numbers_item) | records_df[PHONE_FIELD].isin(phone_numbers_all) | records_df[PHONE_FIELD].isin(exclude)
        records_df = records_df[~rmv]
        if records_df.shape[0] == 0:
            logger.warning("All phone numbers already included! Skipping "+item["name"]+";"+language)
            break
        # Remove records after per-item capacity:
        n_item = len(phone_numbers_item)
        if "capacity" in item:
            if (records_df.shape[0] + n_item) > item["capacity"]:
                n_remain = item["capacity"] - n_item
                records_df = records_df.iloc[range(n_remain)]
        # Remove records after total capacity:
        n_all = len(phone_numbers_all)
        if (records_df.shape[0] + n_all) > params["total_capacity"]:
            n_remain = params["total_capacity"] - n_all
            records_df = records_df.iloc[range(n_remain)]
        # Append phone numbers:
        phone_numbers_item = pd.concat([phone_numbers_item, records_df[PHONE_FIELD]])
        phone_numbers_all = pd.concat([phone_numbers_all, records_df[PHONE_FIELD]])
        # Save outreach info to csv file:
        i = i + 1
        output_file = os.path.join(params["output"], str(i)+"-"+item["name"]+"-"+language+"-outreach.csv")
        n_records = records_df.shape[0]
        logger.info("Saving "+str(n_records)+" phone numbers for "+item["name"]+";"+language+" to "+output_file)
        records_df.to_csv(output_file, index=False)


