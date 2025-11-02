from datetime import datetime, timedelta
import logging
from collections import defaultdict
import os
import hashlib
import tempfile
from typing import Any, Dict, Generator, List
from zoneinfo import ZoneInfo

from bam_core.functions.base import Function
from bam_core.functions.params import Params, Param
from bam_core.settings import SALT
from bam_core.constants import (
    BED_REQUESTS_SCHEMA,
    FULFILLED_REQUESTS_SHEET_NAME,
)
from bam_core.constants import (
    FURNITURE_REQUEST_BED,
    KITCHEN_REQUEST_PLATES,
    KITCHEN_REQUEST_CUPS,
    KITCHEN_REQUEST_POTS_AND_PANS,
    EG_REQUEST_PADS,
    EG_REQUEST_BABY_DIAPERS,
    EG_REQUEST_CLOTHING,
    EG_REQUEST_SCHOOL_SUPPLIES,
    EG_REQUEST_ADULT_DIAPERS,
    EG_REQUEST_SOAP,
    PHONE_FIELD,
)
from bam_core.utils.serde import json_to_obj, obj_to_json
from bam_core.lib.airtable import Airtable

log = logging.getLogger(__name__)

SNAPSHOT_DATE_FORMAT = r"%Y-%m-%d-%H-%M-%S"
SNAPSHOT_DATE_FIELD = "Snapshot Date"


class AnalyzeFulfilledRequests(Function):
    use_cache = False
    params = Params(
        Param(
            name="dry_run",
            type="bool",
            default=True,
            description="If true, data will not be written to the  Google Sheet.",
        )
    )

    OUTPUT_FILEPATH = "website-data/fulfilled-requests.json"
    ANALYSIS_END_DATE = datetime.now().date().isoformat()
    ANALYSIS_START_DATE = (
        datetime.now().date() - timedelta(days=31)
    ).isoformat()
    ANALYSIS_CONFIG = [
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
            "name": "Baby Diapers",
            "translations": {"span": "Pañales para Bebé", "eng": "Baby Diapers"},
            "tags": [EG_REQUEST_BABY_DIAPERS],
        },
        {
            "name": "Adult Diapers",
            "translations": {"span": "Pañales para Adultos", "eng": "Adult Diapers"},
            "tags": [EG_REQUEST_ADULT_DIAPERS],
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
        {
            "name": "Plates",
            "translations": {"span": "Platos", "eng": "Plates"},
            "tags": [KITCHEN_REQUEST_PLATES],
        },
        {
            "name": "Cups",
            "translations": {"span": "Tazas", "eng": "Cups"},
            "tags": [KITCHEN_REQUEST_CUPS],
        },
        {
            "name": "Soap",
            "translations": {"span": "Jabón", "eng": "Soap"},
            "tags": [EG_REQUEST_SOAP],
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
        Get records from Digital Ocean Space with local caching
        """
        grouped_records = defaultdict(list)
        cache_dir = os.path.join(
            tempfile.gettempdir(), "airtable_snapshots_cache"
        )
        os.makedirs(cache_dir, exist_ok=True)

        self.log.info("Fetching snapshots from Digital Ocean Space...")
        if self.use_cache:
            self.log.info(f"Using cache directory: {cache_dir}")
        for filepath in self.s3.list_keys(
            "airtable-snapshots/assistance-requests-main/"
        ):
            if not filepath.endswith(".json"):
                continue

            if self.use_cache:
                cache_file = os.path.join(
                    cache_dir, os.path.basename(filepath)
                )
                if os.path.exists(cache_file):
                    self.log.debug(f"Using cached file for {filepath}")
                    with open(cache_file, "r") as f:
                        contents = f.read()
                else:
                    self.log.debug(f"Fetching records from {filepath}")
                    contents = self.s3.get_contents(filepath).decode("utf-8")
                    with open(cache_file, "w") as f:
                        f.write(contents)
            else:
                self.log.debug(f"Fetching records from {filepath}")
                contents = self.s3.get_contents(filepath).decode("utf-8")

            if contents:
                snapshot_date = self.get_snapshot_date(filepath)
                file_records = json_to_obj(contents)
                for record in file_records:
                    record[SNAPSHOT_DATE_FIELD] = snapshot_date
                    grouped_records[record["id"]].append(record)

        return grouped_records

    def get_fulfilled_requests(
        self, grouped_records: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze grouped records and return a list of fulfilled requests
        """
        fulfilled_requests = []
        # iterate through list of snapshots for each record id
        for record_id, group_records in grouped_records.items():
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
                                        record_id
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

    def get_open_requests_for_snapshot(
        self, record_id: str, snapshot: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get open requests for a snapshot
        """
        # analyze requests for this snapshot
        open_requests = []
        statuses = Airtable.analyze_requests(snapshot)
        for tag_type, tag_statuses in statuses.items():
            for item in tag_statuses.get("open", []):
                h = hashlib.new("sha256")
                h.update((snapshot.get(PHONE_FIELD, "") + SALT).encode())
                phone_number_hash = str(h.hexdigest())
                open_requests.append(
                    {
                        "Request Type": tag_type,
                        "Status": "Open",
                        "Item": item,
                        "Phone Number Hash": phone_number_hash,
                        "Airtable Link": self.airtable.get_assistance_request_link(
                            record_id
                        ),
                    }
                )
        return open_requests

    def get_last_snapshots(
        self, grouped_records: List[Dict[str, Any]]
    ) -> Generator[None, None, Dict[str, Any]]:
        """
        Get the most recent snapshots for every record
        """
        # iterate through list of snapshots for each record id
        for record_id, group_records in grouped_records.items():
            # get most recent snapshot for this record id
            last_snapshot = list(
                sorted(
                    group_records,
                    key=lambda r: r[SNAPSHOT_DATE_FIELD],
                    reverse=True,
                )
            )[0]
            yield record_id, last_snapshot

    def get_open_requests(
        self, grouped_records: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze grouped records and return a list of open requests
        """
        open_requests = []
        # iterate through list of last snapshot for each record id
        for record_id, last_snapshot in self.get_last_snapshots(
            grouped_records
        ):
            open_requests.extend(
                self.get_open_requests_for_snapshot(record_id, last_snapshot)
            )
        return open_requests

    def upload_requests_to_google_sheet(self, requests, sheet_index=0):
        """
        Upload fulfilled requests to Google Sheet
        """
        self.log.info(
            f"Writing requests to Google Sheet: '{FULFILLED_REQUESTS_SHEET_NAME}'"
        )
        self.gsheets.upload_to_sheet(
            sheet_name=FULFILLED_REQUESTS_SHEET_NAME,
            sheet_index=sheet_index,
            data=requests,
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
        tf = os.path.join(td, "fulfilled-requests.json")
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
        fulfilled_requests = self.get_fulfilled_requests(grouped_records)
        self.log.info(f"Found {len(fulfilled_requests)} fulfilled requests")
        open_requests = self.get_open_requests(grouped_records)
        self.log.info(f"Found {len(open_requests)} open requests")
        summary = self.summarize_fulfilled_requests(fulfilled_requests)

        if not params.get("dry_run", False):
            self.upload_requests_to_google_sheet(
                fulfilled_requests, sheet_index=0
            )
            self.upload_requests_to_google_sheet(open_requests, sheet_index=1)
            self.upload_summarized_fulfilled_requests_to_s3(summary)
        else:
            self.log.info(
                "Dry run, not writing fulfilled requests to Google Sheet or summary file Digital Ocean Space."
            )
        return {
            "num_fulfilled_requests": len(fulfilled_requests),
            "num_open_requests": len(open_requests),
            "summary": summary,
        }


if __name__ == "__main__":
    AnalyzeFulfilledRequests().run_cli()
