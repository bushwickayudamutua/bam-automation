from collections import Counter

from pyairtable.api.types import RecordDict

from bam_core.constants import (
    VOLUNTEER_EMAIL_ERROR_FIELD,
    VOLUNTEER_EMAIL_FIELD,
    VOLUNTEER_INVALID_PHONE_FIELD,
    VOLUNTEER_PHONE_NUMBER_FIELD,
    VOLUNTEERS_TABLE_NAME,
)
from bam_core.functions.base import Function
from bam_core.utils.email import NO_EMAIL_ERROR, format_email
from bam_core.utils.phone import format_phone_number


class CleanVolunteerTable(Function):
    """
    Clean phone numbers and email addresses in Airtable
    """

    def clean_phone_number(self, record: RecordDict, counter: Counter[str]):
        """
        Clean phone number and update record if necessary
        """
        record_id = record["id"]
        phone_number = record["fields"].get(VOLUNTEER_PHONE_NUMBER_FIELD)
        was_invalid_phone_number = record["fields"].get(
            VOLUNTEER_INVALID_PHONE_FIELD, False
        )

        # phone number cleaning logic #

        valid_phone_number = False
        if phone_number:
            clean_phone_number = format_phone_number(phone_number)
            if clean_phone_number is not None:
                valid_phone_number = True
                if clean_phone_number != phone_number:
                    self.log.info(
                        f"Changing phone number: {phone_number} to {clean_phone_number} for record: {record_id}"
                    )
                    self.airtable.volunteers.update(
                        record_id,
                        {
                            VOLUNTEER_PHONE_NUMBER_FIELD: clean_phone_number,
                            VOLUNTEER_INVALID_PHONE_FIELD: False,
                        },
                    )
                    counter["n_reformatted_phone_numbers"] += 1

        # mark invalid phone numbers which have not already been marked invalid
        if not valid_phone_number and not was_invalid_phone_number:
            self.log.info(
                f"Marking phone number: {phone_number} as invalid for record: {record_id}"
            )
            self.airtable.volunteers.update(
                record_id, {VOLUNTEER_INVALID_PHONE_FIELD: True}
            )
            counter["n_invalid_phone_numbers"] += 1

        # mark now valid phone numbers which had been previously marked as invalid
        if valid_phone_number and was_invalid_phone_number:
            self.log.info(
                f"Marking phone number: {phone_number} as valid for record: {record_id}"
            )
            self.airtable.volunteers.update(
                record_id, {VOLUNTEER_INVALID_PHONE_FIELD: False}
            )
            counter["n_fixed_phone_numbers"] += 1

        return counter

    def clean_email(self, record: RecordDict, counter: Counter[str]):
        """
        Clean email and update record if necessary
        """
        record_id = record["id"]
        email = record["fields"].get(VOLUNTEER_EMAIL_FIELD)
        prev_email_error = record["fields"].get(VOLUNTEER_EMAIL_ERROR_FIELD)

        valid_email = False
        email_error = ""

        # check for empty emails
        if not email:
            if prev_email_error != NO_EMAIL_ERROR:
                self.log.info(
                    f"Marking email: {email} as invalid for record: {record_id} because of error: {NO_EMAIL_ERROR}"
                )
                self.airtable.volunteers.update(
                    record_id,
                    {
                        VOLUNTEER_EMAIL_FIELD: "",
                        VOLUNTEER_EMAIL_ERROR_FIELD: NO_EMAIL_ERROR,
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
                    self.airtable.volunteers.update(
                        record_id,
                        {
                            VOLUNTEER_EMAIL_FIELD: clean_email,
                            VOLUNTEER_EMAIL_ERROR_FIELD: "",
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
            self.airtable.volunteers.update(
                record_id, {VOLUNTEER_EMAIL_ERROR_FIELD: email_error}
            )
            if email_error != NO_EMAIL_ERROR:
                counter["n_invalid_emails"] += 1
            else:
                counter["n_missing_emails"] += 1

        # mark now valid emails which had been previously marked as invalid
        if valid_email and prev_email_error:
            self.log.info(f"Marking email: {email} as valid for record: {record_id}")
            self.airtable.volunteers.update(
                record_id, {VOLUNTEER_EMAIL_ERROR_FIELD: ""}
            )
            counter["n_fixed_emails"] += 1

        return counter

    def run(self, params):
        """
        Clean volunteer records in Airtable
        """
        self.log.info(f"Fetching {VOLUNTEERS_TABLE_NAME}")
        records = self.airtable.volunteers.all(
            fields=[
                VOLUNTEER_PHONE_NUMBER_FIELD,
                VOLUNTEER_INVALID_PHONE_FIELD,
                VOLUNTEER_EMAIL_FIELD,
                VOLUNTEER_EMAIL_ERROR_FIELD,
            ]  # add more fields here for future cleaning steps.
        )
        self.log.info(f"Cleaning {len(records)} records from {VOLUNTEERS_TABLE_NAME}")
        phone_counter = Counter()
        email_counter = Counter()

        for record in records:
            phone_counter = self.clean_phone_number(record, phone_counter)
            email_counter = self.clean_email(record, email_counter)

        result = {
            "phone_numbers": dict(phone_counter),
            "email_addresses": dict(email_counter),
        }
        self.log.info(f"Result: {result}")
        return result


if __name__ == "__main__":
    CleanVolunteerTable().run_cli()
