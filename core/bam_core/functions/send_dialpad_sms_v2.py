from bam_core.functions.base import Function
from bam_core.functions.params import Param, Params
from bam_core.lib.airtable_v2 import Household
from bam_core.utils.etc import now_est
from datetime import date


class SendDialpadSMSV2(Function):
    """
    Given an Airtable view, send SMS messages to phone numbers in the view via Dialpad.
    """

    params = Params(
        Param(
            name="view_name",
            type="string",
            required=True,
            description="An Airtable view name to fetch Household records from.",
        ),
        Param(
            name="message_template",
            type="string",
            required=True,
            description="The template of the message to send via SMS. Use [FIRST_NAME] to insert the first name and [REQUEST_URL] to insert a request form URL which is randomized so it wont get blocked by Dialpad.",
        ),
        Param(
            name="exclude_texted_today",
            type="bool",
            default=True,
            description="If true, households that were texted today will be excluded.",
        ),
        Param(
            name="max_messages",
            type="int",
            default=None,
            description="The maximum number of messages to send. If not specified, all records across all the views will be processed.",
            required=False,
        ),
        Param(
            name="dry_run",
            type="bool",
            default=True,
            description="If true, messages will not be sent and only logged. Useful for testing.",
        ),
    )

    def run(self, params):
        """
        Snapshot Airtable tables
        """
        view_name = params.get("view_name")
        message = params.get("message_template")
        exclude_texted_today = params.get("exclude_texted_today", True)
        max_messages = params.get("max_messages") or 500
        dry_run = params.get("dry_run", True)

        today = date.today().strftime("%Y-%m-%d")
        households_formula = "NOT(IS_SAME({Last Texted}, '"+today+"'))" if exclude_texted_today else None
        households_all = Household.all(view=view_name, formula=households_formula, max_records=max_messages)

        self.log.info(f"Selected {len(households_all)} households!")
        
        num_messages_sent = 0
        for household in self.dialpad.send_sms_v2(
            households=households_all,
            message=message,
            testing=dry_run,
        ):
            if not household:
                continue
            num_messages_sent += 1
            # update last auto-texted field in Airtable
            if not dry_run:
                self.log.info(f"Setting Last Texted for household {household.bam_id}")
                household.last_texted = now_est().date()
                household.save()
        
        self.log.info(f"Successfully sent {num_messages_sent} messages!")


if __name__ == "__main__":
    SendDialpadSMSV2().run_cli()
