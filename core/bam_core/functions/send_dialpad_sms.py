from bam_core.functions.base import Function
from bam_core.functions.params import Params, Param
from bam_core.constants import ASSISTANCE_REQUESTS_TABLE_NAME
from core.bam_core.utils.etc import now_est


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
            name="message",
            type="string",
            required=True,
            description="The message to send via SMS. Use [FIRST_NAME] to insert the first name and [REQUEST_URL] to insert a random URL.",
        ),
        Param(
            name="max_messages",
            type="int",
            default=None,
            description="The maximum number of messages to send. If not specified, all records in the views will be processed.",
            required=False,
        ),
    )

    def run(self, params, context):
        """
        Snapshot Airtable tables
        """
        view_names = params.get("view_names")
        message = params.get("message")
        max_messages = params.get("max_messages") or 1e9

        seen_phone_numbers = set()
        num_messages_sent = 0
        for view_name in view_names:
            rows = self.airtable.get_view(
                table_name=ASSISTANCE_REQUESTS_TABLE_NAME,
                view_name=view_name,
                fields=[
                    "First Name",
                    "Phone Number",
                ],
                flatten=True,
            )

            # filter out rows with missing phone numbers and deduplicate by phone number
            rows = [
                row
                for row in rows
                if row.get("Phone Number")
                and row.get("Phone Number") not in seen_phone_numbers
            ]

            if not rows:
                self.log.error(f"No valid records found in view: {view_name}")
                continue

            for row in self.dialpad.send_sms(rows=rows, message=message):
                if not row:
                    continue
                num_messages_sent += 1
                phone_number = row.get("Phone Number")
                seen_phone_numbers.add(phone_number)
                # update last auto-texted field in Airtable
                self.airtable.assistance_requests.update(
                    str(row["id"]),
                    fields={
                        "Last Auto Texted": now_est().date().isoformat(),
                    },
                )
                if num_messages_sent >= max_messages:
                    self.log.info(
                        f"Reached max messages limit of {max_messages}"
                    )
                    break


if __name__ == "__main__":
    SendDialpadSMS().run_cli()
