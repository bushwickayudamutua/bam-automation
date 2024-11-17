from datetime import datetime
import logging
from collections import defaultdict
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from .base import Function
from .params import Parameters, Param
from bam_core.constants import FULFILLED_REQUESTS_SHEET_NAME
from bam_core.utils.serde import json_to_obj
from bam_core.lib.airtable import Airtable

log = logging.getLogger(__name__)

SNAPSHOT_DATE_FORMAT = r"%Y-%m-%d-%H-%M-%S"
SNAPSHOT_DATE_FIELD = "Snapshot Date"


class AnalyzeFulfilledRequests(Function):
    params = Parameters(
        Param(
            name="dry_run",
            type="bool",
            default=True,
            description="If true, data will not be written to the  Google Sheet.",
        )
    )

    def get_snapshot_date(self, filepath):
        """
        Get snapshot date from filepath.
        NOTE: This date in the filepath is in EST
        """
        dt = datetime.strptime(
            filepath.split("/assistance-requests-main-")[-1].split(".")[0],
            SNAPSHOT_DATE_FORMAT,
        )
        dt = dt.replace(tzinfo=ZoneInfo("America/New_York"))
        dt = dt.astimezone(ZoneInfo("UTC"))
        return dt.date().isoformat()

    def get_grouped_records(self):
        """
        Get records from Digital Ocean Space
        """
        grouped_records = defaultdict(list)
        self.log.info("Fetching snapshots from Digital Ocean Space...")
        for filepath in self.s3.list_keys(
            "airtable-snapshots/assistance-requests-main/"
        ):
            if not filepath.endswith(".json"):
                continue
            log.debug(f"Fetching records from {filepath}")
            snapshot_date = self.get_snapshot_date(filepath)
            contents = self.s3.get_contents(filepath).decode("utf-8")
            if contents:
                file_records = json_to_obj(contents)
                for record in file_records:
                    record[SNAPSHOT_DATE_FIELD] = snapshot_date
                    grouped_records[record["id"]].append(record)
        return grouped_records

    def analyze_grouped_records(
        self, grouped_records: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze grouped records and return a list of fulfilled requests
        """
        fulfilled_requests = []
        # iterate through list of snapshots for each record id
        for request_id, group_records in grouped_records.items():
            # If there is only one snapshot for this record id, skip it
            if len(group_records) <= 1:
                continue
            last_statuses = {}
            # iterate through snapshots for this record id
            for record in sorted(
                group_records, key=lambda r: r[SNAPSHOT_DATE_FIELD]
            ):
                these_statuses = Airtable.analyze_requests(record)
                # iterate through tag types
                for tag_type, these_tag_statuses in these_statuses.items():
                    # get last statuses for this tag type
                    last_tag_statuses = last_statuses.get(tag_type, {})
                    # iterate through previously open items for this tag type
                    for item in last_tag_statuses.get("open", []):
                        # if this item now has a delivered status
                        # mark it as delivered
                        if item in these_tag_statuses.get("delivered", []):
                            fulfilled_requests.append(
                                {
                                    "Request Type": tag_type,
                                    "Delivered Item": item,
                                    "Date Delivered": record[
                                        SNAPSHOT_DATE_FIELD
                                    ],
                                    "Airtable Link": self.airtable.get_assistance_request_link(
                                        request_id
                                    ),
                                }
                            )
                last_statuses = these_statuses
        return list(
            sorted(
                fulfilled_requests,
                key=lambda r: r["Date Delivered"],
                reverse=True,
            )
        )

    def run(self, params, context):
        """
        Analyze airtable snapshots to identify fulfilled requests and write to a google sheet.
        """
        # fetch records and group by ID
        grouped_records = self.get_grouped_records()
        fulfilled_requests = self.analyze_grouped_records(grouped_records)
        self.log.info(f"Found {len(fulfilled_requests)} fulfilled requests")
        if not params.get("dry_run", False):
            self.log.info(
                f"Writing fulfilled requests to Google Sheet: '{FULFILLED_REQUESTS_SHEET_NAME}'"
            )
            self.gsheets.upload_to_sheet(
                sheet_name=FULFILLED_REQUESTS_SHEET_NAME,
                sheet_index=0,
                data=fulfilled_requests,
            )
        else:
            self.log.info(
                "Dry run, not writing fulfilled requests to Google Sheet"
            )
        return {"num_fulfilled_requests": len(fulfilled_requests)}


if __name__ == "__main__":
    AnalyzeFulfilledRequests().run_cli()
