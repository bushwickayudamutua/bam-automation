import traceback
from collections import Counter
from typing import List, Dict, Any
from pyairtable import formulas

from bam_core.functions.base import Function
from bam_core.functions.params import Params, Param
from bam_core.utils.etc import to_list
from bam_core.constants import (
    EG_REQUESTS_SCHEMA,
    KITCHEN_REQUESTS_SCHEMA,
    FURNITURE_REQUESTS_SCHEMA,
    SOCIAL_SERVICES_REQUESTS_SCHEMA,
    PHONE_FIELD,
)

# handling for request field parameter
REQUEST_SCHEMA_MAP = {
    "eg": EG_REQUESTS_SCHEMA,
    "kitchen": KITCHEN_REQUESTS_SCHEMA,
    "furniture": FURNITURE_REQUESTS_SCHEMA,
    "ss": SOCIAL_SERVICES_REQUESTS_SCHEMA,
}


class TimeoutEssentialGoodsRequests(Function):
    """
    Given:
        * a `REQUEST_FIELD`
            - (Either `eg`, `kitchen`, `furniture`, `ss`)
        * a `REQUEST_VALUE` item
            - (eg `Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴用品`)

    For all records that have an `REQUEST_VALUE` in the `REQUEST_FIELD`, add an associated "timeout" status to any
    unfulfilled records for phone numbers which have at least one later fulfilled request.
    """

    params = Params(
        Param(
            name="view_name",
            type="string",
            description="If included, only requests from phone numbers in this view will be timed out. Later requests will not be closed.",
        ),
        Param(
            name="request_field",
            type="string",
            default="eg",
            description="The field to consider for timing out. Either 'eg', 'kitchen', 'furniture', or 'ss'",
        ),
        Param(
            name="request_value",
            type="string",
            required=True,
            description="The request to timeout. E.g. 'Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴用品'",
        ),
        Param(
            name="dry_run",
            type="bool",
            default=True,
            description="If true, view which timeouts would be added without actually adding them.",
        ),
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
        view_name: str | None,
        request_value: str,
        request_field: str,
        timeout_tags: List[str],
        delivered_tags: List[str],
        status_field: str,
        dry_run: bool,
    ) -> Counter:
        """
        For phone numbers which have at least one fulfilled request,
        timeout all unfulfilled requests submitted before the latest
        fulfilled request.
        """

        cutoffs = None
        if view_name is not None:
            view_records = self.airtable.get_phone_number_to_requests_lookup(view=view_name)

            cutoffs = {
                phone_number: max([rec["createdTime"] for rec in records])
                for phone_number, records in view_records.items()
            }

        # get matching requests
        self.log.info("=" * 60)
        self.log.info(
            f"Fetching records for '{request_field}' = '{request_value}'"
        )
        request_records = self.airtable.get_phone_number_to_requests_lookup(
            formula=formulas.FIND(request_value, formulas.Field(request_field),
            ),
            fields=[PHONE_FIELD, request_field, status_field],
        )
        stats = Counter()
        for phone_number, records in request_records.items():
            latest_delivered_request_created_time = None
            unfulfilled_requests = []
            if cutoffs is None:
                for record in records:
                    created_at = record["createdTime"]
                    statuses = record.get(status_field, [])
                    if any([d in statuses for d in delivered_tags]):
                        if (
                            latest_delivered_request_created_time is None
                            or created_at > latest_delivered_request_created_time
                        ):
                            latest_delivered_request_created_time = created_at
                    elif not any([t in statuses for t in timeout_tags]):
                        # build up list of unfulfilled requests to timeout
                        unfulfilled_requests.append(record)
            else:
                latest_delivered_request_created_time = cutoffs.get(phone_number)
                for record in records:
                    statuses = record.get(status_field, [])
                    if not any([t in statuses for t in delivered_tags + timeout_tags]):
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
                if created_at <= latest_delivered_request_created_time:
                    statuses = list(
                        set(record.get(status_field, []) + timeout_tags)
                    )
                    stats["timedout_requests"] += 1
                    msg = (
                        f"{'Adding' if not dry_run else 'Would add'}"
                        f" '{','.join(timeout_tags)}' to the '{status_field}' field for "
                        f"'{phone_number}' (created_at: {created_at})"
                    )
                    self.log.info(msg)
                    self.update_record(
                        record_id, {status_field: statuses}, dry_run
                    )
        return dict(stats)

    def run(self, params, context):
        # parse view name param
        view_name = params.get("view_name")

        # validate input request field
        request_field_shorthand = params["request_field"].strip()
        if request_field_shorthand not in REQUEST_SCHEMA_MAP:
            raise ValueError(
                f"Invalid REQUEST_FIELD: '{request_field_shorthand}'"
                + "\nChoose from: "
                + ", ".join(REQUEST_SCHEMA_MAP.keys())
            )

        # lookup schema and full request field name
        request_schema = REQUEST_SCHEMA_MAP[request_field_shorthand]
        request_field = request_schema["request_field"]

        # validate request value
        request_value = params["request_value"].strip()
        if request_value not in request_schema["items"]:
            raise ValueError(
                f"Invalid {request_field} request: '{request_value}'"
                + "\nChoose from:\n\t"
                + "\n\t".join(request_schema["items"].keys())
            )

        request_item = request_schema["items"][request_value]

        # get the timeout and delivered tags from the schema
        timeout_tags = to_list(request_item["timeout"]) + to_list(request_item.get("invalid", []))
        delivered_tags = to_list(request_item["delivered"])

        # get the status field to update
        status_field = request_schema["status_field"]

        # parse dry run flag
        dry_run = params.get("dry_run", True)

        if dry_run:
            self.log.warning(
                "Running in DRY_RUN mode. No records will be updated."
            )
        else:
            self.log.warning("Running in LIVE mode. Records will be updated.")

        # run the timeout process
        timeout_stats = self.timeout_requests(
            view_name=view_name,
            request_value=request_value,
            request_field=request_field,
            timeout_tags=timeout_tags,
            delivered_tags=delivered_tags,
            status_field=status_field,
            dry_run=dry_run,
        )

        # report results
        self.log.info("Finished!")
        if not timeout_stats.get("timedout_requests", 0) > 0:
            message = f"No phone numbers had unfulfilled requests for '{request_value}' to timeout."
        else:
            message = (
                f"{timeout_stats['timedout_requests']} unfulfilled requests for '{request_value}' "
                + f"{'would have been' if dry_run else 'were'} timedout by adding '"
                + ",".join(timeout_tags)
                + f"' to the '{status_field}' field."
            )
        self.log.info(message)

        # format and return results
        return {
            "parameters_raw": params,
            "parameters_parsed": {
                "request_field": request_field,
                "request_value": request_value,
                "timeout_tags": timeout_tags,
                "delivered_tags": delivered_tags,
                "status_field": status_field,
                "dry_run": dry_run,
            },
            "stats": timeout_stats,
        }


if __name__ == "__main__":
    TimeoutEssentialGoodsRequests().run_cli()
