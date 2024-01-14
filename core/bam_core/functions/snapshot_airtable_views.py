import os
import logging
import tempfile
from typing import Any, Dict, List
from datetime import timedelta, datetime

from .base import Function
from bam_core.utils.serde import obj_to_json
from bam_core.utils.etc import now_est
from bam_core.constants import AIRTABLE_DATETIME_FORMAT

log = logging.getLogger(__name__)


class SnapshotAirtableViews(Function):
    CONFIG = [
        {
            "table_name": "Assistance Requests: Main",
            "last_modified_field": "Last Modified",
        },
        {
            "table_name": "Volunteers: Main",
            "last_modified_field": "Last Modified",
        },
        {
            "table_name": "Essential Goods Donations: Main",
            "last_modified_field": "Last Modified",
        },
    ]

    def add_options(self):
        self.parser.add_argument(
            "-n",
            dest="NUMBER_OF_DAYS",
            help="The number of days to go back in time to fetch modified records",
            default=1,
        )
        self.parser.add_argument(
            "-d",
            dest="DRY_RUN",
            help="If true, data will not be written to Digital Ocean Space.",
            action="store_true",
            default=False,
        )

    def get_modified_records(
        self,
        table_name: str,
        last_modified_field: str,
        number_of_days: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch modified records from Airtable
        """
        records = []
        for record in self.airtable.get_table(table_name).all():
            fields = record.pop("fields", {})
            record.update(fields)
            if number_of_days is not None:
                last_modified = record.get(last_modified_field, None)
                if last_modified:
                    last_modified = datetime.strptime(
                        last_modified, AIRTABLE_DATETIME_FORMAT
                    )
                    if last_modified.date() >= (
                        datetime.utcnow().date()
                        - timedelta(days=number_of_days)
                    ):
                        records.append(record)
            else:
                records.append(record)
        return records

    def get_slug_from_table_name(self, table_name: str) -> str:
        """
        Get a filepath from a table name
        """
        return table_name.replace(":", "").replace(" ", "-").lower()

    def get_date_slug(self):
        """
        Get a date slug
        NOTE: This is in EST, when we parse this datetime in `analyze_fulfilled_requests.py`, we convert it to UTC.
        """
        return now_est().strftime(r"%Y-%m-%d-%H-%M-%S")

    def get_filepath(self, table_name: str):
        """
        Get a filepath for a table
        """
        slug = self.get_slug_from_table_name(table_name)
        return f"airtable-snapshots/{slug}/{slug}-{self.get_date_slug()}.json"

    def run(self, event, context):
        """
        Snapshot Airtable tables
        """
        number_of_days = event.get("NUMBER_OF_DAYS", 1)
        if str(number_of_days).lower() == "none":
            number_of_days = None
        if number_of_days:
            number_of_days = int(number_of_days)
        dry_run = event.get("DRY_RUN", False)
        output = []
        for config in self.CONFIG:
            table_name = config["table_name"]
            last_modified_field = config["last_modified_field"]
            log.info(f"Fetching modified records from '{table_name}'")
            records = self.get_modified_records(
                table_name, last_modified_field, number_of_days
            )
            if not records:
                log.info(f"No modified records found in {table_name} table")
                continue
            log.info(
                f"Found {len(records)} modified records in {table_name} table"
            )

            # write json to a tempfile and upload to digital ocean space
            tmp = tempfile.NamedTemporaryFile(delete=False)
            filepath = self.get_filepath(table_name)
            if not dry_run:
                log.info(
                    f"Writing {len(records)} records to {tmp.name} and uploading to {filepath}"
                )
                try:
                    tmp.write(obj_to_json(records).encode("utf-8"))
                    self.s3.upload(
                        tmp.name, filepath, mimetype="application/json"
                    )
                finally:
                    tmp.close()
                    os.unlink(tmp.name)
            else:
                log.info(
                    f"Would have written {len(records)} records to {filepath}"
                )
            output.append(
                {
                    "table_name": table_name,
                    "records": len(records),
                    "filepath": filepath,
                }
            )
        return output


if __name__ == "__main__":
    SnapshotAirtableViews().cli()
