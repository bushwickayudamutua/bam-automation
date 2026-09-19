import os
import tempfile
from datetime import datetime, timedelta

from pyairtable.api.types import RecordDict

from bam_core.constants import AIRTABLE_DATETIME_FORMAT, VOLUNTEERS_TABLE_NAME
from bam_core.functions.base import Function
from bam_core.functions.params import Param, Params
from bam_core.utils.etc import now_est, now_utc
from bam_core.utils.serde import obj_to_json

LAST_MODIFIED_FIELD = "Last Modified"


class SnapshotVolunteerTable(Function):
    """
    Fetch modified records from Airtable and upload to Digital Ocean Space
    """

    params = Params(
        Param(
            name="number_of_days",
            type="int",
            default=1,
            description="The number of days to go back in time to fetch modified records",
        ),
        Param(
            name="dry_run",
            type="bool",
            default=True,
            description="If true, data will not be written to Digital Ocean Space.",
        ),
    )

    def get_modified_records(self, number_of_days: int | None) -> list[RecordDict]:
        """
        Fetch modified records from Airtable
        """
        records = []
        for record in self.airtable.volunteers.all():
            if number_of_days is not None:
                last_modified = record.get(LAST_MODIFIED_FIELD, None)
                if last_modified:
                    last_modified = datetime.strptime(
                        last_modified, AIRTABLE_DATETIME_FORMAT
                    )
                    if last_modified.date() >= (
                        now_utc().date() - timedelta(days=number_of_days)
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

    def run(self, params):
        """
        Snapshot Airtable tables
        """
        number_of_days = params.get("number_of_days", 1)
        if str(number_of_days).lower() == "none":
            number_of_days = None
        if number_of_days:
            number_of_days = int(number_of_days)
        dry_run = params.get("dry_run", True)
        self.log.info(f"Fetching modified records from '{VOLUNTEERS_TABLE_NAME}'")
        records = self.get_modified_records(number_of_days)
        if not records:
            self.log.info(f"No modified records found in {VOLUNTEERS_TABLE_NAME} table")
            return
        self.log.info(
            f"Found {len(records)} modified records in {VOLUNTEERS_TABLE_NAME} table"
        )

        # write json to a tempfile and upload to digital ocean space
        tmp = tempfile.NamedTemporaryFile(delete=False)
        filepath = self.get_filepath(VOLUNTEERS_TABLE_NAME)
        if not dry_run:
            self.log.info(
                f"Writing {len(records)} records to {tmp.name} and uploading to {filepath}"
            )
            try:
                tmp.write(obj_to_json(records).encode("utf-8"))
                self.s3.upload(tmp.name, filepath, mimetype="application/json")
            finally:
                tmp.close()
                os.unlink(tmp.name)
        else:
            self.log.info(f"Would have written {len(records)} records to {filepath}")
        return {
            "table_name": VOLUNTEERS_TABLE_NAME,
            "records": len(records),
            "filepath": filepath,
        }


if __name__ == "__main__":
    SnapshotVolunteerTable().run_cli()
