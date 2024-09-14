import logging
from datetime import datetime
from typing import Optional, cast, Dict, Any, NamedTuple

from pyairtable import Api
from bam_core import settings
from bam_core import constants
from bam_core.constants import View
from bam_core.functions.base import Function
from bam_core.utils.etc import to_bool

log = logging.getLogger(__name__)


# record type
class Record(NamedTuple):
    id: int
    phone_number: str
    date_submitted: datetime
    status: list[str]


# connection to assistance requests table
table = Api(settings.AIRTABLE_TOKEN).table(
    settings.AIRTABLE_BASE_ID,
    constants.ASSISTANCE_REQUESTS_TABLE_NAME,
)


def convert_airtable_datestr_to_date(datestr: str) -> datetime:
    """
    >>> convert_airtable_datestr_to_date("2022-09-10T19:53:01.000Z")
    datetime.datetime(2022, 9, 10, 19, 53, 1)
    >>> convert_airtable_datestr_to_date("")
    Traceback (most recent call last):
    ...
    ValueError: time data '' does not match format '%Y-%m-%dT%H:%M:%S'
    """
    return datetime.strptime(datestr.split(".")[0], r"%Y-%m-%dT%H:%M:%S")


def is_invalid_record(record: Record, dupe_flag: str) -> bool:
    """
    >>> invalid_record = Record(id=0, phone_number="", date_submitted="", status=[])
    >>> is_invalid_record(invalid_record, dupe_flag="TEST_FLAG")
    True
    >>> already_flagged_record = Record(0, "516", datetime.now(), ["TEST_FLAG"])
    >>> is_invalid_record(already_flagged_record, dupe_flag="TEST_FLAG")
    True
    >>> valid_record = Record(0, "516", datetime.now(), [])
    >>> is_invalid_record(valid_record, dupe_flag="TEST_FLAG")
    False
    """
    return not record.phone_number or (dupe_flag in record.status)


def set_record_status_as_dupe(
    record: Record, status_field: str, dupe_flag: str, dry_run: bool = False
) -> None:
    new_status = record.status + [dupe_flag]
    if dry_run:
        log.info(
            f"Would have updated record with id {record.id} to have status {new_status}"
        )
        return
    try:
        table.update(
            str(record.id),
            {status_field: new_status, "Phone Number": record.phone_number},
        )
        log.info(
            f"SUCCESS: Changed status {record.status} -> {new_status} "
            + f"for record ID {record.id}, {record.phone_number}"
        )
    except Exception:
        log.exception(
            f"FAILURE: Changing status {record.status} -> {new_status} "
            + f"for record ID {record.id} {record.phone_number}"
        )


def parse_record(
    airtable_record: Dict[str, Any], status_field_name: str, dupe_flag: str
) -> Optional[Record]:
    """Extracts the necessary values for deduplicating from an airtable record."""
    try:
        id = airtable_record["id"]
        datestr = airtable_record["fields"]["Date Submitted"]
        phone_number = airtable_record["fields"]["Phone Number"]
    except KeyError:
        log.warning(
            f"Unable to get all required fields from {airtable_record}"
        )
        return None

    try:
        date_submitted = convert_airtable_datestr_to_date(datestr)
    except ValueError:
        log.exception(
            f"Unable to parse airtable record with {id}: "
            + f"Date {datestr} did not match format {constants.AIRTABLE_DATE_FORMAT}"
        )
        return None

    try:
        status = airtable_record["fields"][status_field_name]
        # because this api is dumb and doesn't always return a list
        if not isinstance(status, list):
            status = [status]
    except KeyError:
        status = []

    record = Record(
        id=id,
        phone_number=phone_number,
        date_submitted=date_submitted,
        status=status,
    )
    if is_invalid_record(record, dupe_flag):
        return None
    return record


def dedupe_view(view: View, dry_run: bool = False) -> None:
    """
    Marks all but the earliest record as duplicate, by adding dupe flag to status field
    """

    def dedupe_records(
        record1: Record, record2: Record, dry_run: bool
    ) -> None:
        """Mark the later record as duplicate."""
        if record1.date_submitted < record2.date_submitted:
            set_record_status_as_dupe(record2, status_field, dupe_flag)
            records_to_keep[record1.phone_number] = record1
        else:
            set_record_status_as_dupe(record1, status_field, dupe_flag)
            records_to_keep[record2.phone_number] = record2

    def dedupe_mesh_records(
        record1: Record, record2: Record, dry_run: bool
    ) -> None:
        """
        If the status field of a record in mesh view is not empty, it is in outreach.
        That means all records with the same phone number without a status
        should be marked as duplicate. Otherwise, dedupe as usual.
        """
        if record1.status and record2.status:
            return
        elif record2.status:
            set_record_status_as_dupe(
                record1, status_field, dupe_flag, dry_run
            )
            records_to_keep[record2.phone_number] = record2
        elif record1.status:
            set_record_status_as_dupe(
                record1, status_field, dupe_flag, dry_run
            )
            records_to_keep[record2.phone_number] = record2
        else:
            dedupe_records(record1, record2, dry_run)

    records_to_keep = {}
    view_name, status_field, dupe_flag = cast(list[str], view.values())
    records: list[Dict[str, Any]] = table.all(
        view=view_name, fields=["Phone Number", "Date Submitted", status_field]
    )

    for record1 in records:
        record1 = parse_record(record1, status_field, dupe_flag)
        if record1 is None:
            continue
        if record1.phone_number not in records_to_keep:
            records_to_keep[record1.phone_number] = record1
            continue

        record2 = records_to_keep[record1.phone_number]
        if view_name == constants.MESH_VIEW_NAME:
            dedupe_mesh_records(record1, record2, dry_run)
        else:
            dedupe_records(record1, record2, dry_run)

    return records_to_keep


class DedupeAirtableViews(Function):
    """
    Dedupe a list of Airtable views by marking all but the earliest
    open records for a phone number as "timed out".
    """

    def add_options(self) -> None:
        self.parser.add_argument(
            "-d",
            dest="DRY_RUN",
            help="If true, update operations will not be performed.",
            action="store_true",
            default=False,
        )

    def run(self, event, context):
        # parse dry run flag
        dry_run = to_bool(event.get("DRY_RUN", True))
        if dry_run:
            log.warning("Running in DRY_RUN mode. No records will be updated.")
        else:
            log.warning("Running in LIVE mode. Records will be updated.")

        for view in constants.VIEWS:
            log.info(f"Deduping view: {view['name']}")
            dedupe_view(view, dry_run)


if __name__ == "__main__":
    DedupeAirtableViews().cli()
