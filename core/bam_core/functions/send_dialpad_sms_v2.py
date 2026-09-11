from bam_core.lib import airtable_v2
from bam_core.functions.base import Function
from bam_core.functions.params import Params, Param
from bam_core.utils.etc import now_est


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
            default=None,
            description="An Airtable view name to retrieve households to exclude from the text blast.",
            required=False,
        ),
        Param(
            name="exclude_texted_today",
            type="bool",
            default=True,
            description="If true, households that were texted today will be excluded.",
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
        exclude_households_view_name = params.get("exclude_households_view_name", None)
        exclude_texted_today = params.get("exclude_texted_today", True)
        dry_run = params.get("dry_run", True)


        requests = airtable_v2.Request.all(view=request_view_name)

        # If formula/view is None, it will be ignored. Skip filtering if both are None.
        exclude_households_formula = "IS_SAME({Last Texted}, TODAY())" if exclude_texted_today else None
        excluded_households = (
            set() if (exclude_households_view_name is None) and (exclude_households_formula is None) else {
                household.bam_id for household in airtable_v2.Household.all(view=exclude_households_view_name, formula=exclude_households_formula)
            }
        )

        msg_recipients = {}
        for request in requests:
            household = request.household
            household_id = household.bam_id
            if household_id in msg_recipients or household_id in excluded_households:
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
                self.log.info(f"Setting Last Texted for household {household.bam_id}")
                household.last_texted = now_est().date()
                household.save()
            if num_messages_sent >= max_messages:
                self.log.info(f"Reached message limit of {max_messages}")
                return

        self.log.info(f"Successfully sent {num_messages_sent} messages!")


if __name__ == "__main__":
    SendDialpadSMSV2().run_cli()
