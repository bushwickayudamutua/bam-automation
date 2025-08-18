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



texted_date_datetime = DATETIME_PARSE('08/12/2025', 'MM/DD/YYYY')
texted_date_str = '2025-08-12'

conditions = AND(*[
    EQ(Field("Last contacted"), texted_date_datetime)
])
fields = [PHONE_FIELD]
records = tutoring_table.all(formula=conditions, fields=fields)
records_df = pd.DataFrame([{"record_id": records[i]["id"], **records[i]["fields"]} for i in range(len(records))])
records_df.shape[0]

record_ids = []
for curr_phone_number in records_df["Phone Number"]:
    conditions = AND(*[
        EQ(Field(PHONE_FIELD), curr_phone_number)
    ])
    fields = ["Case #"]
    curr_records = main_table.all(formula=conditions, fields=fields)
    record_ids = record_ids + [r["id"] for r in curr_records]

update_fields = {"Last Auto Texted": texted_date_str}
batch_update_fields = [{"id": id, "fields": update_fields} for id in record_ids]
update_out = main_table.batch_update(batch_update_fields)



texted_date_datetime = DATETIME_PARSE('7/12/2025', 'MM/DD/YYYY')
texted_date_str = '2025-07-12'

records = main_table.all(formula=EQ(Field("Last Auto Texted"), texted_date_datetime), fields=[PHONE_FIELD])
records_df = pd.DataFrame([{"record_id": records[i]["id"], **records[i]["fields"]} for i in range(len(records))])
records_df.shape[0]

record_ids = []
for curr_phone_number in records_df[PHONE_FIELD]:
    conditions = AND(*[
        EQ(Field(PHONE_FIELD), curr_phone_number)
    ])
    fields = [PHONE_FIELD]
    curr_records = tutoring_table.all(formula=conditions, fields=fields)
    record_ids = record_ids + [r["id"] for r in curr_records]

update_fields = {"Last contacted": texted_date_str}
batch_update_fields = [{"id": id, "fields": update_fields} for id in record_ids]
update_out = tutoring_table.batch_update(batch_update_fields)



tutoring_records = tutoring_table.all(view="Mass texting", fields=[PHONE_FIELD])
tutoring_records_df = pd.DataFrame([{"record_id": tutoring_records[i]["id"], **tutoring_records[i]["fields"]} for i in range(len(tutoring_records))])

pots_pans_records = main_table.all(view="pots and pans", fields=[PHONE_FIELD])
pots_pans_records_df = pd.DataFrame([{"record_id": pots_pans_records[i]["id"], **pots_pans_records[i]["fields"]} for i in range(len(pots_pans_records))])

both = list(set(tutoring_records_df[PHONE_FIELD]) & set(pots_pans_records_df[PHONE_FIELD]))
len(both)
