from bam_core.functions.base import Function
from bam_core.functions.dedupe_airtable_views import DedupeAirtableViews
from bam_core.functions.update_mailjet_lists import UpdateMailjetLists
from bam_core.functions.snapshot_airtable_views import SnapshotAirtableViews
from bam_core.functions.analyze_fulfilled_requests import (
    AnalyzeFulfilledRequests,
)


def main(event, context):
    return Function.run_do_functions(
        event,
        context,
        DedupeAirtableViews,
        UpdateMailjetLists,
        SnapshotAirtableViews,
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 1:
        dry_run = True
    else:
        dry_run = False if sys.argv[1] == "false" else True
    from pprint import pprint

    output = main({"dry_run": dry_run}, {})
    pprint(output)
