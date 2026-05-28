from bam_core.constants import PHONE_FIELD
from bam_core.utils.phone import extract_phone_numbers
from pyairtable import formulas

from bam_core.functions.base import Function
from bam_core.functions.params import Params, Param


class UpdateAirtableFieldValue(Function):
    """
    Update a field in the Assistance Requests table for a list of phone numbers
    """

    params = Params(
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
            name="update_last",
            type="bool",
            description="If true, update only the last record found per phone number. Otherwise, update all records matching the phone numbers",
            default=True,
        ),
        Param(
            name="append",
            type="bool",
            description="If true, `new_value` is appended to the current value in each record. Otherwise, `new_value` replaces the current value",
            default=False,
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
        update_last: bool,
        append: bool,
        view_name: str = "",
        dry_run: bool = True,
    ):
        """
        Update a field for a list of phone numbers
        Args:
            phone_numbers: the list of phone numbers to update
            field_name: the name of the field to update
            new_value: the new value to set
            update_last: whether to update all records per phone number or last
            append: whether to append to or replace the old value
            view_name: the name of the view to use
            dry_run: whether to actually update the records or not
        """

        # construct a formula to get all records that match the list of phone numbers
        get_all_matching_phone_numbers = formulas.OR(
            *[
                formulas.EQ(number, formulas.Field("Phone Number"))
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

        # map phone number to list of matching records
        phone_number_to_records = {}
        for record in records:
            try:
                phone_number = record["fields"][PHONE_FIELD]
                if phone_number not in phone_number_to_records:
                    phone_number_to_records[phone_number] = []
                phone_number_to_records[phone_number].append(record)
            except KeyError:
                self.log.warning(
                    f"Unable to get phone number for record id: {record}"
                )

        for number in phone_numbers:
            try:
                records = phone_number_to_records[number]
                if update_last:
                    records = records[-1:]
            except KeyError:
                self.log.warning(f"Could not find record for number {number}")
                continue

            # append or replace, depending on flag
            for record in records:
                # drop phone number for update purposes, just to be safe
                del record["fields"][PHONE_FIELD]
                if append:
                    record["fields"][field_name] += new_value
                else:
                    record["fields"][field_name] = new_value

            self.log.info(f"Updating {field_name} with {new_value} (append: {append}) for {number}")
            if not dry_run:
                try:
                    self.airtable.assistance_requests.batch_update(records)
                except Exception as e:
                    self.log.error(
                        f"Error updating field {field_name} with {new_value} (append: {append}) for {number}: {e}"
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

        # extract update_last and append flags
        update_last = params.get("update_last", True)
        append = params.get("append", False)

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
            phone_numbers,
            field_name,
            new_value,
            update_last,
            append,
            view_name,
            dry_run,
        )


if __name__ == "__main__":
    UpdateAirtableFieldValue().run_cli()
