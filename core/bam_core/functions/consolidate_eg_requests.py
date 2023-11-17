import logging
import time
import traceback
from pprint import pprint
from collections import defaultdict, Counter
from typing import List, Dict, Any
from pyairtable import formulas

from .base import Function
from bam_core.constants import (
    EG_REQUESTS_SCHEMA,
    EG_REQUESTS_FIELD,
    EG_STATUS_FIELD,
    PHONE_FIELD,
)

log = logging.getLogger(__name__)

# fields to request per view
VIEW_FIELDS = [PHONE_FIELD, EG_REQUESTS_FIELD, EG_STATUS_FIELD]


class ConsolidateEssentialGoodsRequests(Function):
    """
    1. Given:
        * an `ESSENTIAL_GOODS_REQUEST` item
            - (eg `Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴产品`)
        * a `SOURCE_VIEW`, or the associated view of "open" requests for this item
            - (eg `Essential Goods: Soap & Shower Products`)
        * a list of `TARGET_VIEWS`, or other views of "open" requests
            - (eg `["Essential Goods: Pads", "Essential Goods: Baby Diapers"]`)
        For each of the `TARGET_VIEWS`, find any phone numbers that are also in the `SOURCE_VIEW`.
        In the case that a matching record in the `TARGET_VIEW` has an `ESSENTIAL_GOODS_REQUEST`
        and the status is set to "timeout", delete the "timeout" status from the record in the `TARGET_VIEW`
        and add a "timeout" status to the record in the `SOURCE_VIEW`.
        In the case that a  matching record in the `TARGET_VIEW` does not have an `ESSENTIAL_GOODS_REQUEST`,
        add one so it opens a request for this item, and add a "timeout" flag to the record in the `SOURCE_VIEW`,
        thereby closing that request.

    2. For all records that have an `ESSENTIAL_GOODS_REQUEST`, add a "timeout" status to any unfulfilled records
       for phone numbers which have at least one fulfilled request.
    """

    def add_options(self):
        self.parser.add_argument(
            "-r",
            dest="ESSENTIAL_GOODS_REQUEST",
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
        request: str,
        timeout_tag: str,
        delivered_tag: str,
        source_view: str,
        target_views: List[str],
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
            target_lookup = self.airtable.get_phone_number_to_requests_lookup(
                target_view, fields=VIEW_FIELDS
            )
            # wait before fetching the source lookup to ensure changes are reflected
            time.sleep(5)
            source_lookup = self.airtable.get_phone_number_to_requests_lookup(
                source_view, fields=VIEW_FIELDS
            )

            for phone_number, target_records in target_lookup.items():
                # ignore non-matching records
                if phone_number not in source_lookup:
                    continue

                # keep track of the id we modify
                # if it's the same as the source record, there's no need to remove
                # the timeout flag
                consolidated_id = None
                for target_record in target_records:
                    created_at = target_record["createdTime"]
                    status_tags = target_record.get(EG_STATUS_FIELD, [])
                    request_tags = target_record.get(EG_REQUESTS_FIELD, [])

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
                            {EG_STATUS_FIELD: status_tags},
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
                            {EG_REQUESTS_FIELD: request_tags},
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
                    status_tags = source_record.get(EG_STATUS_FIELD, []) + [
                        timeout_tag
                    ]
                    self.update_record(
                        source_record["id"],
                        {EG_STATUS_FIELD: status_tags},
                        dry_run,
                    )

        return stats

    def timeout_requests(
        self, request: str, timeout_tag: str, delivered_tag: str, dry_run: bool
    ) -> Counter:
        """
        For phone numbers which have at least one fulfilled request,
        timeout all unfulfilled requests submitted before the latest
        fulfilled request.
        """
        # get matching requests
        request_records = self.airtable.get_phone_number_to_requests_lookup(
            formula=formulas.FIND(
                formulas.STR_VALUE(request), formulas.FIELD(EG_REQUESTS_FIELD)
            ),
            fields=VIEW_FIELDS,
        )
        stats = Counter()
        for phone_number, records in request_records.items():
            if len(records) == 1:
                # skip phone numbers with only one record
                stats["single_requests"] += 1
                continue

            latest_delivered_request_created_time = None
            unfulfilled_requests = []
            for record in records:
                statuses = record.get(EG_STATUS_FIELD, [])
                if delivered_tag in statuses:
                    if (
                        latest_delivered_request_created_time is None
                        or record["createdTime"]
                        > latest_delivered_request_created_time
                    ):
                        latest_delivered_request_created_time = record[
                            "createdTime"
                        ]
                elif timeout_tag not in statuses:
                    # build up list of unfulfilled requests to timeout
                    unfulfilled_requests.append(record)

            if latest_delivered_request_created_time is None or not len(
                unfulfilled_requests
            ):
                # If there are no delivered requests or unfulfilled requests
                # continue to the next phone number
                continue

            for record in unfulfilled_requests:
                created_at = record["createdTime"]
                if created_at < latest_delivered_request_created_time:
                    statuses = record.get(EG_STATUS_FIELD, [])
                    statuses.append(timeout_tag)
                    stats["timedout_requests"] += 1
                    log.info(
                        f"Adding {timeout_tag} to: {created_at} for phone number: {record['Phone Number']}"
                    )
                    self.update_record(
                        record["id"], {EG_STATUS_FIELD: statuses}, dry_run
                    )
        return stats

    def run(self, event, context):
        # validate the provided request
        request = event["ESSENTIAL_GOODS_REQUEST"]
        if request not in EG_REQUESTS_SCHEMA:
            raise ValueError(
                f"Invalid ESSENTIAL_GOODS_REQUEST: {request}. Choose from: {EG_REQUESTS_SCHEMA.keys()}"
            )

        # get the timeout flag from the schema
        timeout_tag = EG_REQUESTS_SCHEMA[request]["timeout"]
        delivered_tag = EG_REQUESTS_SCHEMA[request]["delivered"]

        # consolidate the view
        consolidate_stats = self.consolidate_view(
            request=request,
            timeout_tag=timeout_tag,
            delivered_tag=delivered_tag,
            source_view=event["SOURCE_VIEW"],
            target_views=event["TARGET_VIEWS"],
            dry_run=event["DRY_RUN"],
        )
        log.info("=" * 60)

        # timeout requests for phone numbers with >= 1 fulfilled request
        timeout_stats = self.timeout_requests(
            request=request,
            timeout_tag=timeout_tag,
            delivered_tag=delivered_tag,
            dry_run=event["DRY_RUN"],
        )
        log.info("Consolidate step finished with stats:\n")
        pprint(dict(consolidate_stats))
        log.info("Timeout step finished with stats:\n")
        pprint(dict(timeout_stats))
        return {
            "consolidate_stats": consolidate_stats,
            "timeout_stats": timeout_stats,
        }


if __name__ == "__main__":
    ConsolidateEssentialGoodsRequests().cli()
