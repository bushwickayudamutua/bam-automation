import pandas as pd
from pyairtable import Api
from datetime import datetime
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

# Update last auto texted field:
outreach_dir_path = "/Users/zakieh.tayyebi/Desktop/outreach_Sep2/"
outreach_csv_paths = [f for f in os.listdir(outreach_dir_path) if re.match(r'.+\.csv', f)]
outreach_csv_paths.sort()
fn = "3-pads_soap-Spanish-outreach-2.csv" # outreach_csv_paths[9]
records_df = pd.read_csv(outreach_dir_path+fn)
texted_date = datetime.today().strftime('%Y-%m-%d')

# sanity check:
fn
records_df.shape[0]
texted_date

# update:
for id in records_df["record_id"]:
    update_out = table.update(id, {"Last Auto Texted": texted_date})

