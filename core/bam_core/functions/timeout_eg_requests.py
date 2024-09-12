import logging
import traceback
from pprint import pprint
from collections import Counter
from typing import List, Dict, Any
from pyairtable import formulas

from .base import Function
from bam_core.utils.etc import to_list
from bam_core.constants import (
    EG_REQUESTS_SCHEMA,
    EG_REQUESTS_FIELD,
    EG_STATUS_FIELD,
    PHONE_FIELD,
    KITCHEN_REQUESTS_SCHEMA,
    FURNITURE_REQUESTS_SCHEMA,
    KITCHEN_REQUESTS_FIELD,
    FURNITURE_REQUESTS_FIELD,
)

log = logging.getLogger(__name__)

# fields to request per view
VIEW_FIELDS = [PHONE_FIELD, EG_STATUS_FIELD]

# handling for request field parameter
REQUEST_SCHEMA_MAP = {
    "eg": EG_REQUESTS_SCHEMA,
    "kitchen": KITCHEN_REQUESTS_SCHEMA,
    "furniture": FURNITURE_REQUESTS_SCHEMA,
}
REQUEST_FIELD_MAP = {
    "eg": EG_REQUESTS_FIELD,
    "kitchen": KITCHEN_REQUESTS_FIELD,
    "furniture": FURNITURE_REQUESTS_FIELD,
}


class TimeoutEssentialGoodsRequests(Function):
    """
    For all records that have an `ESSENTIAL_GOODS_REQUEST`, add a "timeout" status to any
    unfulfilled records for phone numbers which have at least one fulfilled request.
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
        self,
        request_value: str,
        request_field: str,
        status_field: str,
        timeout_tags: List[str],
        delivered_tags: List[str],
        dry_run: bool,
    ) -> Counter:
        """
        For phone numbers which have at least one fulfilled request,
        timeout all unfulfilled requests submitted before the latest
        fulfilled request.
        """

        # get matching requests
        request_records = self.airtable.get_phone_number_to_requests_lookup(
            formula=formulas.FIND(
                formulas.STR_VALUE(request_value),
                formulas.FIELD(request_field),
            ),
            fields=VIEW_FIELDS + [request_field, status_field],
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
                created_at = record["createdTime"]
                statuses = record.get(status_field, [])
                if any([d in statuses for d in delivered_tags]):
                    if (
                        latest_delivered_request_created_time is None
                        or created_at > latest_delivered_request_created_time
                    ):
                        latest_delivered_request_created_time = created_at
                elif any([t not in statuses for t in timeout_tags]):
                    # build up list of unfulfilled requests to timeout
                    unfulfilled_requests.append(record)

            if latest_delivered_request_created_time is None or not len(
                unfulfilled_requests
            ):
                # If there are no delivered requests or unfulfilled requests
                # continue to the next phone number
                continue

            for record in unfulfilled_requests:
                record_id = record["id"]
                created_at = record["createdTime"]
                phone_number = record["Phone Number"]
                if created_at < latest_delivered_request_created_time:
                    statuses = list(
                        set(record.get(status_field, []) + timeout_tags)
                    )
                    stats["timedout_requests"] += 1
                    msg = (
                        f"{'Adding' if dry_run else 'Would add'}"
                        f" {','.join(timeout_tags)} to: {record_id} for phone number: {phone_number}"
                    )
                    log.info(msg)
                    self.update_record(
                        record_id, {status_field: statuses}, dry_run
                    )
        return dict(stats)

    def run(self, event, context):
        # validate the provided request
        request_field_shorthand = event["REQUEST_FIELD"].strip()
        if request_field_shorthand not in REQUEST_SCHEMA_MAP:
            raise ValueError(
                f"Invalid REQUEST_FIELD: {request_field_shorthand}. Choose from: {REQUEST_SCHEMA_MAP.keys()}"
            )

        request_schema = REQUEST_SCHEMA_MAP[request_field_shorthand]
        request_field = REQUEST_FIELD_MAP[request_field_shorthand]
        request_value = event["REQUEST_VALUE"].strip()

        if request_value not in request_schema["items"]:
            raise ValueError(
                f"Invalid {request_field_shorthand} request: '{request_value}. Choose from: {request_schema.keys()}"
            )

        # get the timeout flag from the schema
        timeout_tags = to_list(
            request_schema["items"][request_value]["timeout"]
        )
        delivered_tags = to_list(
            request_schema["items"][request_value]["delivered"]
        )

        # timeout requests for phone numbers with >= 1 fulfilled request
        timeout_stats = self.timeout_requests(
            request_value=request_value,
            request_field=request_field,
            status_field=EG_STATUS_FIELD,
            timeout_tags=timeout_tags,
            delivered_tags=delivered_tags,
            dry_run=bool(event.get("DRY_RUN", False)),
        )
        log.info("Timeout process finished with stats:\n")
        pprint(timeout_stats)
        return timeout_stats


if __name__ == "__main__":
    TimeoutEssentialGoodsRequests().cli()
