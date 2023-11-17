from bam_core.functions.dedupe_airtable_views import DedupeAirtableViews
from bam_core.functions.update_mailjet_lists import UpdateMailjetLists


def main(event, context):
    dedupe_output = DedupeAirtableViews().main(event, context)
    mailjet_output = UpdateMailjetLists().main(event, context)
    return {
        "dedupe_airtable_views": dedupe_output,
        "update_mailjet_lists": mailjet_output,
    }


if __name__ == "__main__":
    main(None, None)
