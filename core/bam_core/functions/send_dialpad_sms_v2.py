from bam_core.lib import airtable_v2
from bam_core.functions.base import Function
from bam_core.functions.params import Params, Param
from bam_core.constants import ASSISTANCE_REQUESTS_TABLE_NAME
from bam_core.utils.etc import now_est
from bam_core.constants import PHONE_FIELD


class SendDialpadSMSV2(Function):
    """
    Given a list of Airtable views, send SMS messages to phone numbers in the view via Dialpad.
    """

    params = Params(
        Param(
            name="request_view_name",
            type="string",
            required=True,
            description="An Airtable view name to fetch request records from.",
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
            name="exclude_households_view_name",
            type="string",
            default=True,
            description="An Airtable view name to retrieve households to exclude from the text blast.",
            required=False,
        ),
        Param(
            name="dry_run",
            type="bool",
            default=True,
            description="If true, messages will not be sent and only logged. Useful for testing.",
        ),
    )

    def run(self, params, context):
        """
        Snapshot Airtable tables
        """
        request_view_name = params.get("request_view_name")
        message = params.get("message_template")
        max_messages = params.get("max_messages") or 1e9
        exclude_households_view_name = params.get("exclude_households_view_name")
        dry_run = params.get("dry_run", True)

        requests = airtable_v2.Request.all(view=request_view_name)
        excluded_households = {
            household.ID
            for household in airtable_v2.Household.all(view=exclude_households_view_name)
        }

        msg_recipients = {}
        for request in requests:
            household = requests.household
            household_id = household.ID
            if household_id in msg_map or household_id in excluded_households:
                continue

            msg_recipients[household_id] = household

        num_messages_sent = 0
        for household in self.dialpad.send_sms_v2(
            households=msg_recipients.values(),
            message=message,
            testing=dry_run
        ):
            if not household:
                continue
            num_messages_sent += 1
            # update last auto-texted field in Airtable
            if not dry_run:
                self.log.info(f"Setting {fields} Airtable")
                household.last_texted = now_est().date().isoformat()
                household.save()
            if num_messages_sent >= max_messages:
                self.log.info(f"Reached message limit of {max_messages}")
                return


if __name__ == "__main__":
    SendDialpadSMSV2().run_cli()
