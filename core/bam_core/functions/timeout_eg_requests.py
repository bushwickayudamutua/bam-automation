import logging
import traceback
from pprint import pprint
from collections import Counter
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


class TimeoutEssentialGoodsRequests(Function):
    """
    For all records that have an `ESSENTIAL_GOODS_REQUEST`, add a "timeout" status to any
    unfulfilled records for phone numbers which have at least one fulfilled request.
    """

    def add_options(self):
        self.parser.add_argument(
            "-r",
            dest="ESSENTIAL_GOODS_REQUEST",
            help="The request to consolidate",
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
        return dict(stats)

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

        # timeout requests for phone numbers with >= 1 fulfilled request
        timeout_stats = self.timeout_requests(
            request=request,
            timeout_tag=timeout_tag,
            delivered_tag=delivered_tag,
            dry_run=event.get("DRY_RUN", False),
        )
        log.info("Timeout process finished with stats:\n")
        pprint(timeout_stats)
        return timeout_stats

if __name__ == "__main__":
    TimeoutEssentialGoodsRequests().cli()
