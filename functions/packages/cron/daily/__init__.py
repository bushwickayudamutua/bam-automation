from bam_core.functions.dedupe_airtable_views import DedupeAirtableViews
from bam_core.functions.mailjet.update_mailjet_lists import UpdateMailjetLists


def main(event, context):
    DedupeAirtableViews().main(event, context)
    UpdateMailjetLists().main(event, context)
