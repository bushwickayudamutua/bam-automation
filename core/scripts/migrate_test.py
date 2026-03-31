# NOTE: MAKE SURE to be on branch "zakieh/test_migration"
import os
os.chdir("/Users/personal/git/bam-automation/core/scripts/")

# NOTE: MAKE SURE the main function has been commented out in "migrate_requests_to_new_base.py"
# Source the migration script:
exec(open("migrate_requests_to_new_base.py").read())

# Extract open requests from a snapshot:
legacy_requests = extract_open_requests_per_household()

# Load table downloaded from airtable filtered by "Expected EG Distro Date"
migrate_table = "/Users/zakieh.tayyebi/Desktop/migrate_table.csv"
selected_numbers = pd.read_csv(migrate_table)["Phone Number"]

# Subset households (phone numbers) to those with a cita:
legacy_requests2 = {num: legacy_requests[num] for num in selected_numbers}
transformed_requests = transform_households(legacy_requests2)

# NOTE: MAKE SURE to turn off automations in the new base and clear all households/requests
# Export data per household:
for h in transformed_requests:
    print(h["Phone Number"])
    load_household(h)
