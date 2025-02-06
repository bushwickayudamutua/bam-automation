import pandas as pd
from pyairtable import Api
from datetime import datetime
import os
import dotenv

# Essential Goods table:
dotenv.load_dotenv()
BAM_AIRTABLE_TOKEN = os.getenv("BAM_AIRTABLE_TOKEN", None)
BAM_AIRTABLE_BASE_ID = os.getenv("BAM_AIRTABLE_BASE_ID", None)
BAM_AIRTABLE_ASSISTANCE_REQUESTS_TABLE_ID = os.getenv("BAM_AIRTABLE_ASSISTANCE_REQUESTS_TABLE_ID", None)
api = Api(BAM_AIRTABLE_TOKEN)
table = api.table(BAM_AIRTABLE_BASE_ID, BAM_AIRTABLE_ASSISTANCE_REQUESTS_TABLE_ID)

# Update last auto texted field:
outreach_csv_path = os.path.join("XXX-outreach.csv")
records_df = pd.read_csv(outreach_csv_path)
texted_date = datetime.today().strftime('%Y-%m-%d')
for id in records_df["record_id"]:
    update_out = table.update(id, {"Last Auto Texted": texted_date})

