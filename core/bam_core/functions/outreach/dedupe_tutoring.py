import pandas as pd
from pyairtable import Api
from pyairtable.formulas import *
from datetime import datetime
from bam_core.constants import *
import os
import numpy as np
import re
import dotenv

dotenv.load_dotenv()
BAM_AIRTABLE_TOKEN = os.getenv("BAM_AIRTABLE_TOKEN", None)
BAM_AIRTABLE_BASE_ID = os.getenv("BAM_AIRTABLE_BASE_ID", None)
BAM_AIRTABLE_ASSISTANCE_REQUESTS_TABLE_ID = os.getenv("BAM_AIRTABLE_ASSISTANCE_REQUESTS_TABLE_ID", None)
main_api = Api(BAM_AIRTABLE_TOKEN)
main_table = main_api.table(BAM_AIRTABLE_BASE_ID, BAM_AIRTABLE_ASSISTANCE_REQUESTS_TABLE_ID)

BAM_AIRTABLE_TUTORING_TOKEN = os.getenv("BAM_AIRTABLE_TUTORING_TOKEN", None)
BAM_AIRTABLE_TUTORING_BASE_ID = os.getenv("BAM_AIRTABLE_TUTORING_BASE_ID", None)
BAM_AIRTABLE_TUTORING_TABLE_ID = os.getenv("BAM_AIRTABLE_TUTORING_TABLE_ID", None)
tutoring_api = Api(BAM_AIRTABLE_TUTORING_TOKEN)
tutoring_table = tutoring_api.table(BAM_AIRTABLE_TUTORING_BASE_ID, BAM_AIRTABLE_TUTORING_TABLE_ID)

TUTORING = "Tutoría estudiantil / Tutoring for students / 學生輔導"
TUTORING_TIMEOUT = SOCIAL_SERVICES_REQUESTS_SCHEMA["items"][TUTORING]["timeout"]
TUTORING_DELIVERED = SOCIAL_SERVICES_REQUESTS_SCHEMA["items"][TUTORING]["delivered"]
FIRST_NAME_FIELD = "First Name"
LANGUAGE_FIELD = "Language"

language_map = {
    "Español / Spanish / 西班牙语": "Spanish",
    "Inglés / English / 英文": "English",
    "Arabic / 阿拉伯語": "Arabic",
    "Chino Mandarín / Mandarin / 普通话": "Mandarin",
    "Chino Cantonese / Cantonese / 广东话": "Cantonese",
    "Chino Toishanese / Toishanese / 台山话": "Toishanese",
    "Portuguese / 葡萄牙語": "Portuguese",
    "Francés / French / 法語": "French",
    "Criollo Haitiano / Haitian Creole / 法屬歸融語": "Haitian Creole",
    "Quechua el dialecto / Quechua Dialect / 克丘亞語": "Quechua Dialect",
    "Tagalo/ Tagalog/ 他加禄语": "Tagalog",
    "Otro / Other / 其他語言": "Other"
}

def shorten_language_name(language_list):
    return [language_map[l] for l in language_list]

conditions = AND(*[
    FIND(TUTORING, Field(SOCIAL_SERVICES_REQUESTS_FIELD)),
    # NOT(FIND(TUTORING_TIMEOUT, Field(SOCIAL_SERVICES_STATUS_FIELD))),
    # NOT(FIND(TUTORING_DELIVERED, Field(SOCIAL_SERVICES_STATUS_FIELD)))
])
fields = [
    "Case #", DATE_SUBMITTED_FIELD,
    PHONE_FIELD, LANGUAGE_FIELD, FIRST_NAME_FIELD,
    LAST_TEXTED_DATE_FIELD
    # SOCIAL_SERVICES_REQUESTS_FIELD, SOCIAL_SERVICES_STATUS_FIELD
]
sort = [PHONE_FIELD, DATE_SUBMITTED_FIELD]
records = main_table.all(formula=conditions, fields=fields, sort=sort)
records_df = pd.DataFrame([{"record_id": records[i]["id"], **records[i]["fields"]} for i in range(len(records))])
records_df["oldest"] = ~records_df.duplicated(subset=[PHONE_FIELD], keep="first")
records_df["newest"] = ~records_df.duplicated(subset=[PHONE_FIELD], keep="last")

existing_records = tutoring_table.all(fields=[PHONE_FIELD, "Last contacted"])
existing_records_df = pd.DataFrame([{"record_id": existing_records[i]["id"], **existing_records[i]["fields"]} for i in range(len(existing_records))])

export_phone_numbers = records_df[PHONE_FIELD].drop_duplicates()
export_phone_numbers = export_phone_numbers[~export_phone_numbers.isin(existing_records_df[PHONE_FIELD])]

export_records = []
for curr_phone_number in export_phone_numbers:
    newest_idx = records_df["newest"] & (records_df[PHONE_FIELD] == curr_phone_number)
    oldest_idx = records_df["oldest"] & (records_df[PHONE_FIELD] == curr_phone_number)
    curr_oldest_request = records_df[oldest_idx][DATE_SUBMITTED_FIELD].values[0]
    curr_newest_request = records_df[newest_idx][DATE_SUBMITTED_FIELD].values[0]
    curr_first_name = records_df[newest_idx][FIRST_NAME_FIELD].values[0]
    curr_language = records_df[newest_idx][LANGUAGE_FIELD].values[0]
    curr_language = shorten_language_name(curr_language)
    export_records.append({
        PHONE_FIELD: curr_phone_number,
        FIRST_NAME_FIELD: curr_first_name,
        LANGUAGE_FIELD: curr_language,
        "Oldest request": curr_oldest_request,
        "Most recent request": curr_newest_request
    })

export_records_df = pd.DataFrame(export_records)

export_languages = export_records_df[LANGUAGE_FIELD]
export_languages = set([x for xs in export_languages.dropna() for x in xs])
export_languages.difference(set(language_map.values()))

update = tutoring_table.batch_create(export_records, typecast=True)



conditions = AND(*[
    FIND(TUTORING, Field(SOCIAL_SERVICES_REQUESTS_FIELD)),
    EQ(Field("Last Auto Texted"), DATETIME_PARSE('08/12/2025', 'MM/DD/YYYY'))
])
records = main_table.all(formula=conditions, fields=fields)
records_df = pd.DataFrame([{"record_id": records[i]["id"], **records[i]["fields"]} for i in range(len(records))])
texted_today = records_df[PHONE_FIELD].drop_duplicates()
texted_today.shape[0]

tutoring_records = tutoring_table.all(fields=[PHONE_FIELD, "Last contacted"])
tutoring_records_df = pd.DataFrame([{"record_id": tutoring_records[i]["id"], **tutoring_records[i]["fields"]} for i in range(len(tutoring_records))])
update_records_df = tutoring_records_df[tutoring_records_df[PHONE_FIELD].isin(texted_today)]
update_records_df.shape[0]

update_records = [
    {"id": record_id, "fields": {"Last contacted": "2025-08-12"}}
    for record_id in update_records_df["record_id"]
]
update = tutoring_table.batch_update(update_records)

