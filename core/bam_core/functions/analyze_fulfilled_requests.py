import os
import tempfile
import json
from datetime import datetime, timedelta
import shutil
from typing import Any, Dict, Generator, List, Optional
from memory_profiler import profile

from bam_core.functions.base import Function
from bam_core.functions.params import Params, Param
from bam_core.constants import FULFILLED_REQUESTS_SHEET_NAME, REQUEST_FIELDS
from bam_core.lib.airtable import Airtable


SNAPSHOT_DATE_FORMAT = r"%Y-%m-%d-%H-%M-%S"
SNAPSHOT_DATE_FIELD = "Snapshot Date"


class AnalyzeFulfilledRequests(Function):
    params = Params(
        Param(
            name="dry_run",
            type="bool",
            default=True,
            description="If true, data will not be written to the Google Sheet.",
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
        dt = dt - timedelta(hours=5)  # Convert EST to UTC manually
        return dt.date().isoformat()

    def get_snapshot_files(self):
        """
        Fetch snapshot files from Digital Ocean Space
        """
        return self.s3.list_keys(
            "airtable-snapshots/assistance-requests-main/"
        )

    def get_snapshot_records(self, filepath):
        """
        Fetch snapshot file from Digital Ocean Space
        """
        contents = self.s3.get_contents(filepath).decode("utf-8")
        if contents:
            return json.loads(contents)
        return []

    def write_snapshot_records(self, temp_dir, snapshot_date, records):
        """
        Write snapshot records to temp directory
        """
        for record in records:
            small_record = {
                k: v for k, v in record.items() if k in REQUEST_FIELDS
            }
            small_record[SNAPSHOT_DATE_FIELD] = snapshot_date
            record_id = record["id"]
            record_dir = os.path.join(temp_dir, record_id)
            os.makedirs(record_dir, exist_ok=True)
            record_file = os.path.join(record_dir, f"{snapshot_date}.json")
            with open(record_file, "w") as f:
                json.dump(small_record, f)
                f.close()

    def write_grouped_records(self):
        """
        Get records from Digital Ocean Space and write them to temp directory
        """
        temp_dir = tempfile.mkdtemp()
        self.log.info(f"Temporary directory created at {temp_dir}")
        self.log.info("Fetching snapshots from Digital Ocean Space...")
        for filepath in self.get_snapshot_files():
            if not filepath.endswith(".json"):
                continue
            snapshot_date = self.get_snapshot_date(filepath)
            file_records = self.get_snapshot_records(filepath)
            self.write_snapshot_records(temp_dir, snapshot_date, file_records)
            del file_records
        return temp_dir

    def analyze_requests_for_record(
        self, temp_dir, record_id: str
    ) -> Generator[None, None, Optional[Dict[str, Any]]]:
        record_dir = os.path.join(temp_dir, record_id)
        if not os.path.isdir(record_dir):
            return None
        group_records = []
        # iterate through files in the record directory
        for record_file in os.listdir(record_dir):
            record_path = os.path.join(record_dir, record_file)
            with open(record_path, "r") as f:
                group_records.append(json.load(f))
                f.close()
        # If there is only one snapshot for this record id, skip it
        if len(group_records) <= 1:
            return None
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
                        yield {
                            "Request Type": tag_type,
                            "Delivered Item": item,
                            "Date Delivered": record[SNAPSHOT_DATE_FIELD],
                            "Airtable Link": self.airtable.get_assistance_request_link(
                                record_id
                            ),
                        }
            last_statuses = these_statuses

    def analyze_grouped_records(self, temp_dir: str) -> List[Dict[str, Any]]:
        """
        Analyze grouped records from temp directory and return a list of fulfilled requests
        """
        fulfilled_requests = []
        # iterate through directories for each record id
        for record_id in os.listdir(temp_dir):
            for fulfilled_request in self.analyze_requests_for_record(
                temp_dir, record_id
            ):
                if fulfilled_request:
                    fulfilled_requests.append(fulfilled_request)

        return list(
            sorted(
                fulfilled_requests,
                key=lambda r: r["Date Delivered"],
                reverse=True,
            )
        )

    def run(self, params, _):
        """
        Analyze airtable snapshots to identify fulfilled requests and write to a google sheet.
        """
        # fetch records and group by ID
        temp_dir = None
        try:
            temp_dir = self.write_grouped_records()
            fulfilled_requests = self.analyze_grouped_records(temp_dir)
            self.log.info(
                f"Found {len(fulfilled_requests)} fulfilled requests"
            )
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
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir)


if __name__ == "__main__":
    AnalyzeFulfilledRequests().run_cli()
