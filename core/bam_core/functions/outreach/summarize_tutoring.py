import pandas as pd
from pyairtable import Api
from pyairtable.formulas import *
from datetime import datetime
from bam_core.constants import *
import os
import numpy as np
import re
import dotenv

BAM_AIRTABLE_TUTORING_TOKEN = os.getenv("BAM_AIRTABLE_TUTORING_TOKEN", None)
BAM_AIRTABLE_TUTORING_BASE_ID = os.getenv("BAM_AIRTABLE_TUTORING_BASE_ID", None)
BAM_AIRTABLE_TUTORING_TABLE_ID = os.getenv("BAM_AIRTABLE_TUTORING_TABLE_ID", None)
tutoring_api = Api(BAM_AIRTABLE_TUTORING_TOKEN)
tutoring_table = tutoring_api.table(BAM_AIRTABLE_TUTORING_BASE_ID, BAM_AIRTABLE_TUTORING_TABLE_ID)

conditions = EQ(Field("Still interested in tutoring"), "Yes")
records = tutoring_table.all(formula=conditions)
records_df = pd.DataFrame([{"record_id": records[i]["id"], **records[i]["fields"]} for i in range(len(records))])
records_df.shape[0]

records_df.to_csv("/Users/zakieh.tayyebi/Desktop/tutoring_tb.csv")


