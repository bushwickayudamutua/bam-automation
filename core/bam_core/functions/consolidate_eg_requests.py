import logging
import time
import traceback
from pprint import pprint
from collections import defaultdict, Counter
from typing import List, Dict, Any

from .base import Function
from bam_core.constants import (
    EG_REQUESTS_SCHEMA,
    EG_REQUESTS_FIELD,
    KITCHEN_REQUESTS_SCHEMA,
    KITCHEN_REQUESTS_FIELD,
    FURNITURE_REQUESTS_SCHEMA,
    FURNITURE_REQUESTS_FIELD,
    EG_STATUS_FIELD,
    PHONE_FIELD,
)

log = logging.getLogger(__name__)

# minimum set of fields to request per view
BASE_VIEW_FIELDS = [PHONE_FIELD]

# handling for request field parameter
REQUEST_SCHEMA_MAP = {
    'eg': EG_REQUESTS_SCHEMA,
    'kitchen': KITCHEN_REQUESTS_SCHEMA,
    'furniture': FURNITURE_REQUESTS_SCHEMA,
}
REQUEST_FIELD_MAP = {
    'eg': EG_REQUESTS_FIELD,
    'kitchen': KITCHEN_REQUESTS_FIELD,
    'furniture': FURNITURE_REQUESTS_FIELD,
}


class ConsolidateEssentialGoodsRequests(Function):
    """
    Given:
        * a `REQUEST_FIELD`
            - (Either `eg`, `kitchen`, `furniture`)
        * an `REQUEST_VALUE` item
            - (eg `Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴产品`)
        * a `SOURCE_VIEW`, or the associated view of "open" requests for this item
            - (eg `Essential Goods: Soap & Shower Products`)
        * a list of `TARGET_VIEWS`, or other views of "open" requests
            - (eg `["Essential Goods: Pads", "Essential Goods: Baby Diapers"]`)
    For each of the `TARGET_VIEWS`, find any phone numbers that are also in the `SOURCE_VIEW`.
    In the case that a matching record in the `TARGET_VIEW` has a request in the specified field,
    and the status is set to "timeout", delete the "timeout" status from the record in the `TARGET_VIEW`
    and add a "timeout" status to the record in the `SOURCE_VIEW`.
    In the case that a  matching record in the `TARGET_VIEW` does not have a request of the specified type,
    add one so it opens a request for this item, and add a "timeout" flag to the record in the `SOURCE_VIEW`,
    thereby closing that request.
    """

    def add_options(self):
        self.parser.add_argument(
            "-f",
            dest="REQUEST_FIELD",
            help="The field to consider for consolidation. Either 'eg', 'kitchen', or 'furniture'",
            default="eg",
        )
        self.parser.add_argument(
            "-r",
            dest="REQUEST_VALUE",
            help="The request to consolidate",
            required=True,
        )
        self.parser.add_argument(
            "-s",
            dest="SOURCE_VIEW",
            help="The source view to consolidate requests from",
            required=True,
        )
        self.parser.add_argument(
            "-t",
            dest="TARGET_VIEWS",
            help="The target view to consolidate requests to",
            nargs="+",
            required=True,
        )
        self.parser.add_argument(
            "-d",
            dest="DRY_RUN",
            help="If true, update operations will not be performed.",
            action="store_true",
            default=False,
        )

    def update_record(
        self, id: str, fields: Dict[str, Any], dry_run: bool
    ) -> None:
        """
        Update an assistance request record
        """
        if not dry_run:
            try:
                self.airtable.assistance_requests.update(str(id), fields)
            except Exception:
                traceback.print_exc()

    def consolidate_view(
        self,
        request_field: str,
        request: str,
        timeout_tag: str,
        delivered_tag: str,
        source_view: str,
        target_views: List[str],
        status_field: str = EG_STATUS_FIELD,
        dry_run: bool = False,
    ) -> Dict[str, Counter]:
        """
        Consolidate matching records from source_view to target_views for a request
        """

        stats = defaultdict(Counter)
        for target_view in target_views:
            log.info("=" * 60)
            log.info(
                f"Consolidating: {request}\nFrom: {source_view} To: {target_view}"
            )
            fields = [*BASE_VIEW_FIELDS, request_field, status_field]
            target_lookup = self.airtable.get_phone_number_to_requests_lookup(
                target_view, fields=fields
            )
            # wait before fetching the source lookup to ensure changes are reflected
            time.sleep(5)
            source_lookup = self.airtable.get_phone_number_to_requests_lookup(
                source_view, fields=fields
            )

            for phone_number, target_records in target_lookup.items():
                # ignore non-matching records
                if phone_number not in source_lookup:
                    continue

                # keep track of the id we modify
                # if it's the same as the source record,
                # there's no need to remove the timeout flag
                consolidated_id = None
                for target_record in target_records:
                    created_at = target_record["createdTime"]
                    status_tags = target_record.get(status_field, [])
                    request_tags = target_record.get(request_field, [])

                    if (
                        request in request_tags
                        and delivered_tag in status_tags
                    ):
                        # ignore delivered requests
                        continue

                    elif (
                        request in request_tags and timeout_tag in status_tags
                    ):
                        consolidated_id = target_record["id"]
                        # remove timeout flag
                        log.info(
                            f"(Target - {created_at}) Removing: {timeout_tag} From: {phone_number} In: {target_view}"
                        )
                        stats[target_view]["timeouts_removed"] += 1
                        status_tags.remove(timeout_tag)
                        self.update_record(
                            target_record["id"],
                            {status_field: status_tags},
                            dry_run,
                        )

                    elif request not in request_tags:
                        consolidated_id = target_record["id"]
                        # add request
                        log.info(
                            f"(Target - {created_at}) Adding: {request} To: {phone_number} In: {target_view}"
                        )
                        stats[target_view]["requests_added"] += 1
                        request_tags.append(request)
                        self.update_record(
                            target_record["id"],
                            {request_field: request_tags},
                            dry_run,
                        )

                if not consolidated_id:
                    # if we didn't update a record, continue to the next phone number
                    stats[target_view]["records_skipped"] += 1
                    continue

                # add timeout flag to source records
                for source_record in source_lookup[phone_number]:
                    created_at = source_record["createdTime"]
                    if source_record["id"] == consolidated_id:
                        # this shouldn't ever happen
                        stats[source_view]["records_overlapped"] += 1
                        continue
                    log.info(
                        f"(Source - {created_at}) Adding: {timeout_tag} To: {phone_number} In: {source_view}"
                    )
                    stats[source_view]["timeouts_added"] += 1
                    status_tags = source_record.get(status_field, []) + [
                        timeout_tag
                    ]
                    self.update_record(
                        source_record["id"],
                        {status_field: status_tags},
                        dry_run,
                    )

        return dict(stats)

    def run(self, event, context):
        # validate the provided request
        request_field_shorthand = event["REQUEST_FIELD"].strip()
        request_field = REQUEST_FIELD_MAP.get(request_field_shorthand)
        schema = REQUEST_SCHEMA_MAP.get(request_field_shorthand)
        if not request_field or not schema:
            raise ValueError(
                f"Invalid REQUEST_FIELD: {request_field_shorthand}. Choose from: {REQUEST_SCHEMA_MAP.keys()}"
            )
        request = event["REQUEST_VALUE"].strip()
        if request not in schema["items"]:
            raise ValueError(
                f"Invalid REQUEST_VALUE {request_field}: {request}. Choose from: {schema['items'].keys()}"
            )

        # get the timeout flag from the schema
        timeout_tag = schema["items"][request]["timeout"]
        delivered_tag = schema["items"][request]["delivered"]

        # consolidate the view
        consolidate_stats = self.consolidate_view(
            request_field=request_field,
            request=request,
            timeout_tag=timeout_tag,
            delivered_tag=delivered_tag,
            source_view=event["SOURCE_VIEW"],
            target_views=event["TARGET_VIEWS"],
            dry_run=bool(event.get("DRY_RUN", False)),
        )
        log.info("Consolidation finished with stats:\n")
        pprint(consolidate_stats)
        return consolidate_stats


if __name__ == "__main__":
    ConsolidateEssentialGoodsRequests().cli()
