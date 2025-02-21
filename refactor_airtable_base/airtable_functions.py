import dotenv
import os
import pandas as pd
import pyairtable
from pyairtable import Api
from pyairtable.formulas import *
from datetime import datetime

def get_new_bam_table() -> dict[pyairtable.api.table.Table]:
    dotenv.load_dotenv()
    BAM_AIRTABLE_TOKEN = os.getenv("BAM_AIRTABLE_TOKEN", None)
    BAM_AIRTABLE_BASE_ID = os.getenv("BAM_AIRTABLE_BASE_ID_NEW", None)
    api = Api(BAM_AIRTABLE_TOKEN)
    table = {
        "Households": api.table(BAM_AIRTABLE_BASE_ID, os.getenv("BAM_AIRTABLE_HOUSEHOLDS_TABLE_ID_NEW", None)),
        "Requests": api.table(BAM_AIRTABLE_BASE_ID, os.getenv("BAM_AIRTABLE_REQUESTS_TABLE_ID_NEW", None)),
        "Appointments": api.table(BAM_AIRTABLE_BASE_ID, os.getenv("BAM_AIRTABLE_APPOINTMENTS_TABLE_ID_NEW", None)),
        "Assistance Request Form Submissions": api.table(BAM_AIRTABLE_BASE_ID, os.getenv("BAM_AIRTABLE_ASSISTANCE_SUBMISSIONS_TABLE_ID_NEW", None)),
        "Fulfilled Request Count": api.table(BAM_AIRTABLE_BASE_ID, os.getenv("BAM_AIRTABLE_FULFILLED_REQUESTS_TABLE_ID_NEW", None)),
    }
    return table

def get_old_bam_table() -> pyairtable.api.table.Table:
    dotenv.load_dotenv()
    BAM_AIRTABLE_TOKEN = os.getenv("BAM_AIRTABLE_TOKEN", None)
    BAM_AIRTABLE_BASE_ID = os.getenv("BAM_AIRTABLE_BASE_ID", None)
    BAM_AIRTABLE_ASSISTANCE_REQUESTS_TABLE_ID = os.getenv("BAM_AIRTABLE_ASSISTANCE_REQUESTS_TABLE_ID", None)
    api = Api(BAM_AIRTABLE_TOKEN)
    table = api.table(BAM_AIRTABLE_BASE_ID, BAM_AIRTABLE_ASSISTANCE_REQUESTS_TABLE_ID)
    return table

def records_list_to_df(records_list: list) -> pd.DataFrame:
    records_df = pd.DataFrame([{"id": records_list[i]["id"], "createdTime": records_list[i]["createdTime"], **records_list[i]["fields"]} for i in range(len(records_list))])
    return records_df

