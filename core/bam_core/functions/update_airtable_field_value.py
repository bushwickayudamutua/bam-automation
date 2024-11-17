from bam_core.constants import PHONE_FIELD
from bam_core.utils.phone import extract_phone_numbers
from pyairtable import formulas

from .params import Param, Parameters
from .base import Function


class UpdateAirtableFieldValue(Function):
    """
    Update a field in the Assistance Requests table for a list of phone numbers
    """

    params = Parameters(
        Param(
            name="phone_numbers_to_update",
            type="string",
            description="The text containing the phone numbers to update",
            required=True,
        ),
        Param(
            name="field_name",
            type="string",
            description="The name of the field to update",
            required=True,
        ),
        Param(
            name="new_value",
            type="string",
            description="The new value to set for the field",
            required=True,
        ),
        Param(
            name="view_name",
            type="string",
            description="The optional name of the view to use",
            default=None,
        ),
        Param(
            name="dry_run",
            type="bool",
            description="If true, update operations will not be performed.",
            default=True,
        ),
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
                self.log.warning(
                    f"Unable to get phone number for record id: {record}"
                )

        for number in phone_numbers:
            try:
                record = phone_number_to_records[number]
            except KeyError:
                self.log.warning(f"Could not find record for number {number}")
                continue

            self.log.info(f"Updating {field_name} to {new_value} for {number}")
            if not dry_run:
                try:
                    self.airtable.assistance_requests.update(
                        str(record["id"]), {field_name: new_value}
                    )
                except Exception as e:
                    self.log.error(
                        f"Error updating field {field_name} to {new_value} for {number}: {e}"
                    )
                    raise e

    def run(self, params, context):
        # extract phone numbers from text
        text = params["phone_numbers_to_update"]
        phone_numbers = extract_phone_numbers(text)
        if not phone_numbers:
            raise ValueError(
                f"No phone numbers read from the inputted text: {text}"
            )
        self.log.info(f"Found {len(phone_numbers)} phone numbers in text.")

        # extract field name, new value, and view name
        field_name = params["field_name"].strip()
        new_value = params["new_value"].strip()
        view_name = params.get("view_name", None)

        # parse dry run flag
        dry_run = params.get("dry_run", True)
        if dry_run:
            self.log.warning(
                "Running in DRY_RUN mode. No records will be updated."
            )
        else:
            self.log.warning("Running in LIVE mode. Records will be updated.")

        # run the updates
        self.update_field(
            phone_numbers, field_name, new_value, view_name, dry_run
        )


if __name__ == "__main__":
    UpdateAirtableFieldValue().run_cli()
