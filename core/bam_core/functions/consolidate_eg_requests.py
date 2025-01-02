import time
import traceback
from collections import defaultdict, Counter
from typing import List, Dict, Any


from bam_core.functions.base import Function
from bam_core.functions.params import Params, Param
from bam_core.utils.etc import to_bool, to_list
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

# minimum set of fields to request per view
BASE_VIEW_FIELDS = [PHONE_FIELD]

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

STATUS_FIELD_MAP = {
    "eg": EG_STATUS_FIELD,
    "kitchen": EG_STATUS_FIELD,
    "furniture": EG_STATUS_FIELD,
}


class ConsolidateEssentialGoodsRequests(Function):
    """
    Given:
        * a `REQUEST_FIELD`
            - (Either `eg`, `kitchen`, `furniture`)
        * an `REQUEST_VALUE` item
            - (eg `Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴用品`)
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

    params = Params(
        Param(
            name="request_field",
            type="string",
            description="The field to consider for consolidation. Either 'eg', 'kitchen', or 'furniture'",
            default="eg",
        ),
        Param(
            name="request_value",
            type="string",
            description="The request to consolidate. E.g. 'Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴用品'",
            required=True,
        ),
        Param(
            name="source_view",
            type="string",
            description="The source view to consolidate requests from",
            required=True,
        ),
        Param(
            name="target_views",
            type="string_list",
            description="The target view to consolidate requests to",
            required=True,
        ),
        Param(
            name="dry_run",
            type="bool",
            description="If true, update operations will not be performed.",
            default=True,
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

    def consolidate_view(
        self,
        request_field: str,
        request_value: str,
        timeout_tags: List[str],
        delivered_tags: List[str],
        source_view: str,
        target_views: List[str],
        status_field: str,
        dry_run: bool = False,
    ) -> Dict[str, Counter]:
        """
        Consolidate matching records from source_view to target_views for a request
        """

        stats = defaultdict(Counter)
        for target_view in target_views:
            self.log.info("=" * 60)
            self.log.info(
                f"Consolidating: {request_value}\nFrom: {source_view} To: {target_view}"
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

                    if request_value in request_tags and any(
                        [dt in status_tags for dt in delivered_tags]
                    ):
                        # ignore delivered requests
                        continue

                    elif request_value in request_tags and any(
                        [tt in status_tags for tt in timeout_tags]
                    ):
                        consolidated_id = target_record["id"]
                        # remove timeout flag
                        tag_list = ", ".join(timeout_tags)
                        self.log.info(
                            f"(Target - {created_at}) Removing: {tag_list} From: {phone_number} In: {target_view}"
                        )
                        stats[target_view]["timeouts_removed"] += 1
                        for tt in timeout_tags:
                            if tt in status_tags:
                                status_tags.remove(tt)
                        self.update_record(
                            target_record["id"],
                            {status_field: status_tags},
                            dry_run,
                        )

                    elif request_value not in request_tags:
                        consolidated_id = target_record["id"]
                        # add request
                        self.log.info(
                            f"(Target - {created_at}) Adding: {request_value} To: {phone_number} In: {target_view}"
                        )
                        stats[target_view]["requests_added"] += 1
                        request_tags.append(request_value)
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
                    tag_list = ", ".join(timeout_tags)
                    self.log.info(
                        f"(Source - {created_at}) Adding: {tag_list} To: {phone_number} In: {source_view}"
                    )
                    stats[source_view]["timeouts_added"] += 1
                    status_tags = list(
                        set(source_record.get(status_field, []) + timeout_tags)
                    )
                    self.update_record(
                        source_record["id"],
                        {status_field: status_tags},
                        dry_run,
                    )

        return dict(stats)

    def run(self, params, context):
        # parse the request field
        request_field_shorthand = params["request_field"].strip()
        request_field = REQUEST_FIELD_MAP.get(request_field_shorthand)
        schema = REQUEST_SCHEMA_MAP.get(request_field_shorthand)
        if not request_field or not schema:
            raise ValueError(
                f"Invalid REQUEST_FIELD: {request_field_shorthand}. Choose from: {REQUEST_SCHEMA_MAP.keys()}"
            )

        # validate request value
        request_value = params["request_value"].strip()
        if request_value not in schema["items"]:
            raise ValueError(
                f"Invalid REQUEST_VALUE {request_field}: {request_value}. Choose from: {schema['items'].keys()}"
            )
        # get the status field
        status_field = STATUS_FIELD_MAP.get(request_field_shorthand)

        # get the timeout flag from the schema
        timeout_tags = to_list(schema["items"][request_value]["timeout"])
        delivered_tags = to_list(schema["items"][request_value]["delivered"])

        # parse source + target views to be a list
        source_view = params["source_view"].strip()
        target_views = [t.strip() for t in to_list(params["target_views"])]

        # parse dry run flag
        dry_run = to_bool(params.get("dry_run", True))
        if dry_run:
            self.log.warning(
                "Running in DRY_RUN mode. No records will be updated."
            )
        else:
            self.log.warning("Running in LIVE mode. Records will be updated.")

        # consolidate the views
        consolidate_stats = self.consolidate_view(
            request_field=request_field,
            request_value=request_value,
            timeout_tags=timeout_tags,
            delivered_tags=delivered_tags,
            source_view=source_view,
            target_views=target_views,
            status_field=status_field,
            dry_run=dry_run,
        )
        self.log.info(
            f"Consolidation finished with stats:\ {consolidate_stats}"
        )

        # format and return the results
        return {
            "parameters_raw": params,
            "parameters_parsed": {
                "request_field": request_field,
                "request_value": request_value,
                "timeout_tags": timeout_tags,
                "delivered_tags": delivered_tags,
                "source_view": source_view,
                "target_views": target_views,
                "dry_run": dry_run,
            },
            "stats": consolidate_stats,
        }


if __name__ == "__main__":
    ConsolidateEssentialGoodsRequests().run_cli()
