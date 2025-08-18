import pandas as pd
from pyairtable import Api
from datetime import datetime
from bam_core.constants import *
import os
import re
import dotenv

# Essential Goods table:
dotenv.load_dotenv()
BAM_AIRTABLE_TOKEN = os.getenv("BAM_AIRTABLE_TOKEN", None)
BAM_AIRTABLE_BASE_ID = os.getenv("BAM_AIRTABLE_BASE_ID", None)
BAM_AIRTABLE_ASSISTANCE_REQUESTS_TABLE_ID = os.getenv("BAM_AIRTABLE_ASSISTANCE_REQUESTS_TABLE_ID", None)
api = Api(BAM_AIRTABLE_TOKEN)
table = api.table(BAM_AIRTABLE_BASE_ID, BAM_AIRTABLE_ASSISTANCE_REQUESTS_TABLE_ID)

fields = ["Case #", PHONE_FIELD, FIRST_NAME_FIELD]
records = table.all(view="submitted_2025")
records_df = pd.DataFrame([{"record_id": records[i]["id"], **records[i]["fields"]} for i in range(len(records))])

texted_tb = pd.concat([pd.read_csv(fn) for fn in [
    "/Users/zakieh.tayyebi/Desktop/english-1-filtered.csv",
    "/Users/zakieh.tayyebi/Desktop/spanish-1-filtered.csv",
    "/Users/zakieh.tayyebi/Desktop/spanish-2-filtered.csv"
]])

records_df = records_df[records_df["Phone Number"].isin(texted_tb["Phone Number"])]
records_df.shape[0]

texted_date = '2025-05-09'
# update:
for id in records_df["record_id"]:
    update_out = table.update(id, {"Last Auto Texted": texted_date})

