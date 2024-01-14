from bam_core.functions.base import Function
from bam_core.functions.dedupe_airtable_views import DedupeAirtableViews
from bam_core.functions.update_mailjet_lists import UpdateMailjetLists
from bam_core.functions.snapshot_airtable_views import SnapshotAirtableViews
from bam_core.functions.analyze_fulfilled_requests import AnalyzeFulfilledRequests


def main(event, context):
    return Function.run_functions(
        event,
        context,
        DedupeAirtableViews,
        UpdateMailjetLists,
        SnapshotAirtableViews,
        AnalyzeFulfilledRequests
    )


if __name__ == "__main__":
    from pprint import pprint

    output = main({}, {})
    pprint(output)
