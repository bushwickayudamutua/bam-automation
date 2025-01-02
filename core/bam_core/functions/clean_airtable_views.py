from collections import Counter
from typing import Any, Dict

from bam_core.functions.base import Function
from bam_core.utils.phone import format_phone_number
from bam_core.utils.email import format_email, NO_EMAIL_ERROR


class CleanAirtableViews(Function):
    """
    Clean phone numbers and email addresses in Airtable
    """

    CONFIG = [
        {
            "table_name": "Assistance Requests: Main",
            "view_name": "Raw Data: DO NOT EDIT OR CHANGE FILTERS!",
        },
        {
            "table_name": "Volunteers: Main",
            "view_name": "Raw Data: DO NOT EDIT",
        },
    ]

    def clean_phone_number(self, record, table, counter):
        """
        Clean phone number and update record if necessary
        """
        record_id = record["id"]
        phone_number = record["fields"].get("Phone Number", None)
        was_invalid_phone_number = record["fields"].get(
            "Invalid Phone Number?", False
        )

        # phone number cleaning logic #

        valid_phone_number = False
        clean_phone_number = None
        if phone_number:
            clean_phone_number = format_phone_number(phone_number)
            if clean_phone_number is not None:
                valid_phone_number = True
                if clean_phone_number != phone_number:
                    self.log.info(
                        f"Changing phone number: {phone_number} to {clean_phone_number} for record: {record_id}"
                    )
                    table.update(
                        record_id,
                        {
                            "Phone Number": clean_phone_number,
                            "Invalid Phone Number?": False,
                        },
                    )
                    counter["n_reformatted_phone_numbers"] += 1

        # mark invalid phone numbers which have not already been marked invalid
        if not valid_phone_number and not was_invalid_phone_number:
            self.log.info(
                f"Marking phone number: {phone_number} as invalid for record: {record_id}"
            )
            table.update(record_id, {"Invalid Phone Number?": True})
            counter["n_invalid_phone_numbers"] += 1

        # mark now valid phone numbers which had been previously marked as invalid
        if valid_phone_number and was_invalid_phone_number:
            self.log.info(
                f"Marking phone number: {phone_number} as valid for record: {record_id}"
            )
            table.update(record_id, {"Invalid Phone Number?": False})
            counter["n_fixed_phone_numbers"] += 1

        return counter

    def clean_email(self, record, table, counter):
        """
        Clean email and update record if necessary
        """
        record_id = record["id"]
        email = record["fields"].get("Email", None)
        prev_email_error = record["fields"].get("Email Error", None)

        valid_email = False
        clean_email = None
        email_error = ""

        # check for empty emails
        if not email:
            if prev_email_error != NO_EMAIL_ERROR:
                self.log.info(
                    f"Marking email: {email} as invalid for record: {record_id} because of error: {NO_EMAIL_ERROR}"
                )
                table.update(
                    record_id,
                    {
                        "Email": "",
                        "Email Error": NO_EMAIL_ERROR,
                    },
                )
                counter["n_missing_emails"] += 1

        else:
            email_info = format_email(email)
            clean_email = email_info["email"]
            email_error = email_info["error"]
            if not email_error:
                valid_email = True
                if clean_email != email:
                    self.log.info(
                        f"Changing email: {email} to {clean_email} for record: {record_id}"
                    )
                    table.update(
                        record_id,
                        {
                            "Email": clean_email,
                            "Email Error": "",
                        },
                    )
                    counter["n_reformatted_emails"] += 1

        # mark invalid emails which have not already been marked as invalid
        if email and not valid_email and email_error != prev_email_error:
            if not email:
                email_error = str(NO_EMAIL_ERROR)
            self.log.info(
                f"Marking email: {email} as invalid for record: {record_id} because of error: {email_error}"
            )
            table.update(record_id, {"Email Error": email_error})
            if email_error != NO_EMAIL_ERROR:
                counter["n_invalid_emails"] += 1
            else:
                counter["n_missing_emails"] += 1

        # mark now valid emails which had been previously marked as invalid
        if valid_email and prev_email_error:
            self.log.info(
                f"Marking email: {email} as valid for record: {record_id}"
            )
            table.update(record_id, {"Email Error": ""})
            counter["n_fixed_emails"] += 1

        return counter

    def clean_view(self, view_to_clean: Dict[str, str]) -> Dict[str, Any]:
        """
        Clean a view of records in Airtable
        """
        self.log.info(
            f"Fetching {view_to_clean['table_name']}--{view_to_clean['view_name']}"
        )
        table = self.airtable.get_table(view_to_clean["table_name"])
        records = self.airtable.get_view(
            table_name=view_to_clean["table_name"],
            view_name=view_to_clean["view_name"],
            fields=[
                "Phone Number",
                "Invalid Phone Number?",
                "Email",
                "Email Error",
            ],  # add more fields here for future cleaning steps.
        )
        self.log.info(
            f"Cleaning {len(records)} records from {view_to_clean['table_name']}--{view_to_clean['view_name']}"
        )
        phone_counter = Counter()
        email_counter = Counter()

        for record in records:
            phone_counter = self.clean_phone_number(
                record, table, phone_counter
            )
            email_counter = self.clean_email(record, table, email_counter)

        return {
            "view": view_to_clean,
            "phone_numbers": dict(phone_counter),
            "email_addresses": dict(email_counter),
        }

    def run(self, event, context):
        """
        Clean all views in config.yml
        """
        results = []
        for view_to_clean in self.CONFIG:
            result = self.clean_view(view_to_clean)
            results.append(result)
        self.log.info(f"Results: {results}")
        return results


if __name__ == "__main__":
    CleanAirtableViews().run_cli()
