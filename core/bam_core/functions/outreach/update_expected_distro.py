import pandas as pd
from pyairtable import Api
from pyairtable.formulas import *
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

conditions = AND(*[
    OR(
        EQ(Field(LAST_TEXTED_DATE_FIELD), DATETIME_PARSE('07/21/2025', 'MM/DD/YYYY')),
        EQ(Field(EXPECTED_EG_DATE_FIELD), DATETIME_PARSE('07/22/2025', 'MM/DD/YYYY'))
    )
])
fields = ["Case #", PHONE_FIELD, FIRST_NAME_FIELD]
records = table.all(formula=conditions, fields=fields)
records_df = pd.DataFrame([{"record_id": records[i]["id"], **records[i]["fields"]} for i in range(len(records))])

pref = "/Users/zakieh.tayyebi/Desktop/"
name = "confirmed_July22"
confirmed_cita = pd.read_csv(pref+name+".csv")
confirmed_cita = pd.merge(confirmed_cita, records_df, how="left", on=PHONE_FIELD)
confirmed_cita.dropna().shape[0]

confirmed_cita[[FIRST_NAME_FIELD, PHONE_FIELD]].to_csv(pref+name+"_names.csv")

cita = '2025-07-22'
# update:
for id in confirmed_cita["record_id"].dropna():
    update_out = table.update(id, {EXPECTED_EG_DATE_FIELD: cita})

