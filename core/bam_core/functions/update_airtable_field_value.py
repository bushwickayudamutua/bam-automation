import logging
import traceback

from bam_core.constants import PHONE_FIELD
from bam_core.utils.phone import extract_phone_numbers
from bam_core.utils.etc import to_bool
from pyairtable import formulas

from .base import Function

log = logging.getLogger(__name__)


class UpdateAirtableFieldValue(Function):
    """
    Update a field in the Assistance Requests table for a list of phone numbers
    """

    def add_options(self):
        self.parser.add_argument(
            "-p",
            dest="PHONE_NUMBERS_TO_UPDATE",
            help="The text containing the phone numbers to update",
            required=True,
        )
        self.parser.add_argument(
            "-f",
            dest="FIELD_NAME",
            help="The name of the field to update",
            required=True,
        )
        self.parser.add_argument(
            "-n",
            dest="NEW_VALUE",
            help="The new value to set for the field",
            required=True,
        )
        self.parser.add_argument(
            "-v",
            dest="VIEW_NAME",
            help="The optional name of the view to use",
            default=None,
        )
        self.parser.add_argument(
            "-d",
            dest="DRY_RUN",
            help="If true, update operations will not be performed.",
            action="store_true",
            default=False,
        )

    def update_field(
        self,
        phone_numbers: list[str],
        field_name: str,
        new_value: str,
        view_name: str = "",
        dry_run: bool = True,
    ):
        """
        Update a field for a list of phone numbers
        Args:
            phone_numbers: the list of phone numbers to update
            field_name: the name of the field to update
            new_value: the new value to set
            view_name: the name of the view to use
            dry_run: whether to actually update the records or not
        """

        # construct a formula to get all records that match the list of phone numbers
        get_all_matching_phone_numbers = formulas.OR(
            *[
                formulas.EQUAL(
                    formulas.STR_VALUE(number), formulas.FIELD("Phone Number")
                )
                for number in phone_numbers
            ]
        )

        kwargs = {
            "fields": ["Phone Number", field_name],
            "formula": get_all_matching_phone_numbers,
        }
        if view_name:
            kwargs["view"] = view_name

        records = self.airtable.assistance_requests.all(**kwargs)

        phone_number_to_records = {}
        for record in records:
            try:
                phone_number_to_records[record["fields"][PHONE_FIELD]] = record
            except KeyError:
                log.warning(
                    f"Unable to get phone number for record id: {record}"
                )

        for number in phone_numbers:
            try:
                record = phone_number_to_records[number]
            except KeyError:
                log.warning(f"Could not find record for number {number}")
                continue

            log.info(f"Updating {field_name} to {new_value} for {number}")
            if not dry_run:
                try:
                    self.airtable.assistance_requests.update(
                        str(record["id"]), {field_name: new_value}
                    )
                except Exception as e:
                    log.error(
                        f"Error updating field {field_name} to {new_value} for {number}"
                    )
                    traceback.print_exc()
                    raise e

    def run(self, event, context):
        if not "PHONE_NUMBERS_TO_UPDATE" in event:
            raise ValueError("PHONE_NUMBERS_TO_UPDATE is required")
        if not "FIELD_NAME" in event:
            raise ValueError("FIELD_NAME is required")
        if not "NEW_VALUE" in event:
            raise ValueError("NEW_VALUE is required")
        text = event["PHONE_NUMBERS_TO_UPDATE"]
        phone_numbers = extract_phone_numbers(text)
        log.info(f"Found {len(phone_numbers)} phone numbers in text.")
        if not phone_numbers:
            log.error(f"No phone numbers read from the inputted text: {text}")
            return
        field_name = event["FIELD_NAME"]
        new_value = event["NEW_VALUE"]
        view_name = event.get("VIEW_NAME", None)

        # parse dry run flag
        dry_run = to_bool(event.get("DRY_RUN", True))
        if dry_run:
            log.warning("Running in DRY_RUN mode. No records will be updated.")
        else:
            log.warning("Running in LIVE mode. Records will be updated.")

        self.update_field(
            phone_numbers, field_name, new_value, view_name, dry_run
        )


if __name__ == "__main__":
    UpdateAirtableFieldValue().cli()
