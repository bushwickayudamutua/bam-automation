from datetime import datetime, timedelta
import logging
from collections import defaultdict
import os
import tempfile
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from .base import Function
from .params import Params, Param
from bam_core.constants import (
    BED_REQUESTS_SCHEMA,
    FULFILLED_REQUESTS_SHEET_NAME,
)
from bam_core.constants import (
    FURNITURE_REQUEST_BED,
    KITCHEN_REQUEST_POTS_AND_PANS,
    EG_REQUEST_PADS,
    EG_REQUEST_BABY_DIAPERS,
    EG_REQUEST_CLOTHING,
    EG_REQUEST_SCHOOL_SUPPLIES,
    FOOD_REQUEST_GROCERIES,
)
from bam_core.utils.serde import json_to_obj, obj_to_json
from bam_core.lib.airtable import Airtable

log = logging.getLogger(__name__)

SNAPSHOT_DATE_FORMAT = r"%Y-%m-%d-%H-%M-%S"
SNAPSHOT_DATE_FIELD = "Snapshot Date"


class AnalyzeFulfilledRequests(Function):
    params = Params(
        Param(
            name="dry_run",
            type="bool",
            default=True,
            description="If true, data will not be written to the  Google Sheet.",
        )
    )

    OUTPUT_FILEPATH = "website-data/delivered-requests.json"
    ANALYSIS_END_DATE = datetime.now().date().isoformat()
    ANALYSIS_START_DATE = (
        datetime.now().date() - timedelta(days=31)
    ).isoformat()
    ANALYSIS_CONFIG = [
        {
            "name": "Groceries",
            "translations": {"span": "Comida", "eng": "Groceries"},
            "tags": [FOOD_REQUEST_GROCERIES],
        },
        {
            "name": "Pots and Pans",
            "translations": {
                "span": "Ollas y sartenes",
                "eng": "Pots and Pans",
            },
            "tags": [KITCHEN_REQUEST_POTS_AND_PANS],
        },
        {
            "name": "Beds",
            "translations": {"span": "Camas", "eng": "Beds"},
            "tags": [FURNITURE_REQUEST_BED]
            + list(BED_REQUESTS_SCHEMA["items"].keys()),
        },
        {
            "name": "Pads",
            "translations": {"span": "Toallas sanitarias", "eng": "Pads"},
            "tags": [EG_REQUEST_PADS],
        },
        {
            "name": "Diapers",
            "translations": {"span": "Pañales", "eng": "Diapers"},
            "tags": [EG_REQUEST_BABY_DIAPERS],
        },
        {
            "name": "Clothing Assistance",
            "translations": {"span": "Ropa", "eng": "Clothing Assistance"},
            "tags": [EG_REQUEST_CLOTHING],
        },
        {
            "name": "School Supplies",
            "translations": {
                "span": "Útiles escolares",
                "eng": "School Supplies",
            },
            "tags": [EG_REQUEST_SCHOOL_SUPPLIES],
        },
    ]

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

    def upload_fulfilled_requests_to_google_sheet(self, fulfilled_requests):
        """
        Upload fulfilled requests to Google Sheet
        """
        self.log.info(
            f"Writing fulfilled requests to Google Sheet: '{FULFILLED_REQUESTS_SHEET_NAME}'"
        )
        self.gsheets.upload_to_sheet(
            sheet_name=FULFILLED_REQUESTS_SHEET_NAME,
            sheet_index=0,
            data=fulfilled_requests,
        )

    def summarize_fulfilled_item(
        self, fulfilled_requests: List[Dict[str, Any]], tags: List[str]
    ) -> int:
        """
        Summarize fulfilled requests for a specific tag
        """
        num_requests = len(
            [
                r
                for r in fulfilled_requests
                if r["Delivered Item"] in tags
                and r["Date Delivered"] >= self.ANALYSIS_START_DATE
            ]
        )
        self.log.info(
            f"Found {num_requests} requests for {tags} since {self.ANALYSIS_START_DATE}"
        )
        return num_requests

    def summarize_fulfilled_requests(
        self, fulfilled_requests: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        summary = []
        for config in self.ANALYSIS_CONFIG:
            config["value"] = self.summarize_fulfilled_item(
                fulfilled_requests, config["tags"]
            )
            summary.append(config)
        return {
            "start_date": self.ANALYSIS_START_DATE,
            "end_date": self.ANALYSIS_END_DATE,
            "metrics": summary,
        }

    def upload_summarized_fulfilled_requests_to_s3(
        self, summary: List[Dict[str, Any]]
    ):
        td = tempfile.gettempdir()
        tf = os.path.join(td, "delivered-counts.json")
        with open(tf, "w") as f:
            f.write(obj_to_json(summary))
        fp = self.s3.upload(
            tf, self.OUTPUT_FILEPATH, mimetype="application/json"
        )
        self.s3.set_public(fp)
        self.log.info(f"Uploaded summary file to Digital Ocean Space: {fp}")
        self.s3.purge_cdn_cache(self.OUTPUT_FILEPATH)
        self.log.info(
            f"Purged CDN cache for summary file: {self.OUTPUT_FILEPATH}"
        )

    def run(self, params, context):
        """
        Analyze airtable snapshots to identify fulfilled requests and write to a google sheet.
        """
        # fetch records and group by ID
        grouped_records = self.get_grouped_records()
        fulfilled_requests = self.analyze_grouped_records(grouped_records)
        self.log.info(f"Found {len(fulfilled_requests)} fulfilled requests")
        summary = self.summarize_fulfilled_requests(fulfilled_requests)

        if not params.get("dry_run", False):
            self.upload_fulfilled_requests_to_google_sheet(fulfilled_requests)
            self.upload_summarized_fulfilled_requests_to_s3(summary)
        else:
            self.log.info(
                "Dry run, not writing fulfilled requests to Google Sheet or summary file Digital Ocean Space."
            )
        return {
            "num_fulfilled_requests": len(fulfilled_requests),
            "summary": summary,
        }


if __name__ == "__main__":
    AnalyzeFulfilledRequests().run_cli()
