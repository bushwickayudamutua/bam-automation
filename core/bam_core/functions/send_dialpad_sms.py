from bam_core.functions.base import Function
from bam_core.functions.params import Params, Param
from bam_core.constants import ASSISTANCE_REQUESTS_TABLE_NAME
from bam_core.utils.etc import now_est
from bam_core.constants import PHONE_FIELD


class SendDialpadSMS(Function):
    """
    Given a list of Airtable views, send SMS messages to phone numbers in the view via Dialpad.
    """

    params = Params(
        Param(
            name="view_names",
            type="string_list",
            required=True,
            description="A list of Airtable view names to fetch records from. These should be ordered by priority, with the first view being the highest priority.",
        ),
        Param(
            name="message_template",
            type="string",
            required=True,
            description="The template of the message to send via SMS. Use [FIRST_NAME] to insert the first name and [REQUEST_URL] to insert a request form URL which is randomized so it wont get blocked by Dialpad.",
        ),
        Param(
            name="max_messages",
            type="int",
            default=None,
            description="The maximum number of messages to send. If not specified, all records across all the views will be processed.",
            required=False,
        ),
        Param(
            name="dedupe_phone_numbers",
            type="bool",
            default=True,
            description="Whether to prevent sending multiple messages to the same phone number across all views. If set to False, messages will be sent to all phone numbers in the views.",
            required=False,
        ),
        Param(
            name="dry_run",
            type="bool",
            default=True,
            description="If true, messages will not be sent and only logged. Useful for testing.",
        ),
    )

    def dedupe_view_by_phone_number(self, rows, seen_phone_numbers):
        """
        Deduplicate rows by phone number, keeping only the first occurrence of each phone number.
        :param rows: List of rows to deduplicate
        :param seen_phone_numbers: Set of phone numbers already seen in previous veiws
        :return: List of deduplicated rows
        """
        deduped_rows = []
        phone_numbers_in_these_rows = set()
        for row in rows:
            phone_number = row.get(PHONE_FIELD)
            if (
                phone_number
                and phone_number not in seen_phone_numbers
                and phone_number not in phone_numbers_in_these_rows
            ):
                phone_numbers_in_these_rows.add(phone_number)
                deduped_rows.append(row)
        return deduped_rows

    def run(self, params, context):
        """
        Snapshot Airtable tables
        """
        view_names = params.get("view_names")
        message = params.get("message_template")
        max_messages = params.get("max_messages") or 1e9
        dedupe_phone_numbers = params.get("dedupe_phone_numbers", True)
        dry_run = params.get("dry_run", True)

        seen_phone_numbers = set()
        num_messages_sent = 0
        for view_name in view_names:
            rows = self.airtable.get_view(
                table_name=ASSISTANCE_REQUESTS_TABLE_NAME,
                view_name=view_name,
                fields=[
                    "First Name",
                    PHONE_FIELD,
                ],
                flatten=True,
            )

            # filter out rows with missing phone numbers
            rows = [row for row in rows if row.get("Phone Number")]

            # optionally deduplicate rows in this view by phone number
            if dedupe_phone_numbers:
                rows = self.dedupe_view_by_phone_number(
                    rows, seen_phone_numbers
                )

            if not rows:
                self.log.error(
                    f"No valid records found in view: '{view_name}'"
                )
                continue

            for row in self.dialpad.send_sms(
                rows=rows, message=message, testing=dry_run
            ):
                if not row:
                    continue
                num_messages_sent += 1
                seen_phone_numbers.add(row.get("Phone Number"))
                # update last auto-texted field in Airtable
                if not dry_run:
                    fields = {
                        "Last Auto Texted": now_est().date().isoformat(),
                    }
                    self.log.info(f"Setting {fields} Airtable")
                    self.airtable.assistance_requests.update(
                        str(row["id"]), fields=fields
                    )
                if num_messages_sent >= max_messages:
                    self.log.info(f"Reached message limit of {max_messages}")
                    return


if __name__ == "__main__":
    SendDialpadSMS().run_cli()
