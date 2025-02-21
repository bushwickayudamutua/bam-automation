from airtable_functions import *

FIELDS = [
    "Case #", "Phone Number", "First Name", "Email","Language",
    "Case Notes", "Date Submitted", "Last Auto Texted", 
    "Essential Goods Requests?", "Which Kitchen Items",
    "Essential Goods Requests Status", "Expected EG Distribution Date",
    # "Which Furniture Items", "Which Bed Size",
    # "Food Requests?", "Food Request Status", "Expected Food Distribution Date",
    # "Social Services Requests?", "Social Services Request Status"
]

# 200 random phone numbers:
phone_numbers = pd.read_csv("phone_numbers.csv")["Phone Number"]

# get the old requests table fropm "Intake Form":
old_table = get_old_bam_table()

# get new tables from "BAM Refactor POC":
new_table = get_new_bam_table()

# collect all records for this phone number, sorted by oldest first:
i = 100
records = old_table.all(formula=EQ(Field("Phone Number"), phone_numbers[i]), sort=["Date Submitted"], fields=FIELDS)
records = records_list_to_df(records)

