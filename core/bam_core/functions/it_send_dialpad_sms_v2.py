from bam_core.lib.airtable_v2 import Household
from bam_core.functions.base import Function
from bam_core.functions.params import Params, Param
from bam_core.utils.etc import now_est
import yaml

class ItSendDialpadSMSV2(Function):
    """
    Given an Airtable view, iterate over EG items and languages, and send SMS messages to phone numbers in the view via Dialpad.
    """

    params = Params(
        Param(
            name="view_name",
            type="string",
            required=True,
            description="An Airtable view name to fetch Household records from.",
        ),
        Param(
            name="distro_day",
            type="string",
            required=True,
            description="The day of EG distro. Must be defined in 'message_template' for each language.",
        ),
        Param(
            name="EG_items",
            type="string_list",
            required=True,
            description="The EG items to text for. Must be defined in 'item_label' for each language.",
        ),
        Param(
            name="languages",
            type="string_list",
            required=True,
            description="The languages to text in. Must be included in 'item_label' and 'message_template' parameters.",
        ),
        Param(
            name="volunteer",
            type="string_list",
            required=True,
            description="Name of the volunteer sending sms messages. Must match the order of 'languages'",
        ),
        Param(
            name="message_template",
            type="string",
            required=True,
            description="Path to the yaml file with the template(s) of the message to send via SMS.",
        ),
        Param(
            name="item_label",
            type="string",
            required=True,
            description="Path to the yaml file with the EG item labels in different languages.",
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
            default=500,
            description="The maximum number of messages to send. If not specified, the default maximum is 500.",
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
        view_name = params.get("view_name")
        distro_day = params.get("distro_day")
        EG_items = params.get("EG_items")
        languages = params.get("languages")
        volunteer = params.get("volunteer")
        message_template_yaml = params.get("message_template")
        item_label_yaml = params.get("item_label")
        exclude_texted_today = params.get("exclude_texted_today", True)
        max_messages = params.get("max_messages", 500)
        dry_run = params.get("dry_run", True)

        with open(message_template_yaml, 'r') as file:
            message_template_pars = yaml.safe_load(file)

        with open(item_label_yaml, 'r') as file:
            item_label_pars = yaml.safe_load(file)

        for item in EG_items:
            for lang in languages:
                message_template_yaml[]
                item_label_yaml[item][lang]
        
        households_formula = "NOT(IS_SAME({Last Texted}, TODAY()))" if exclude_texted_today else None
        households_all = Household.all(view=view_name, formula=households_formula, max_records=max_messages)

        self.log.info(f"Selected {len(households_all)} households!")
        
        num_messages_sent = 0
        for household in self.dialpad.send_sms_v2(
            households=households_all,
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
        
        self.log.info(f"Successfully sent {num_messages_sent} messages!")


if __name__ == "__main__":
    SendDialpadSMSV2().run_cli()
