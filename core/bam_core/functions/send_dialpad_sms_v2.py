import logging

from pydantic import Field

from bam_core.functions.base import Function
from bam_core.lib.airtable_v2 import Household
from bam_core.lib.dialpad import Dialpad
from bam_core.utils.etc import now_est

logger = logging.getLogger(__name__)
dialpad = Dialpad(parent_logger=logger)


class SendDialpadSMSV2(Function):
    """
    Given an Airtable view, send SMS messages to phone numbers in the view via Dialpad.
    """

    view_name: str = Field(
        description="An Airtable view name to fetch Household records from."
    )
    message_template: str = Field(
        description="The template of the message to send via SMS. Use [FIRST_NAME] to insert the first name and [REQUEST_URL] to insert a request form URL which is randomized so it wont get blocked by Dialpad."
    )
    exclude_texted_today: bool = Field(
        True,
        description="If true, households that were texted today will be excluded.",
    )
    max_messages: int | None = Field(
        None,
        description="The maximum number of messages to send. If not specified, all records across all the views will be processed.",
    )
    dry_run: bool = Field(
        True,
        description="If true, messages will not be sent and only logged. Useful for testing.",
    )

    def run(self):
        """
        Snapshot Airtable tables
        """
        # Pull records from the Households view (and exclude last texted today by default):
        today_date = now_est().date()
        households_formula = (
            Household.last_texted.ne(today_date) if self.exclude_texted_today else None
        )
        households_all = Household.all(
            view=self.view_name,
            formula=households_formula,
            max_records=self.max_messages,
        )

        logger.info(f"Selected {len(households_all)} households!")

        num_messages_sent = 0
        for household in dialpad.send_sms_v2(
            households=households_all,
            message_template=self.message_template,
            testing=self.dry_run,
        ):
            if not household:
                continue
            num_messages_sent += 1
            # update last auto-texted field in Airtable
            if not self.dry_run:
                logger.info(f"Setting Last Texted for household {household.bam_id}")
                household.last_texted = today_date
                household.save()

        logger.info(f"Successfully sent {num_messages_sent} messages!")


if __name__ == "__main__":
    SendDialpadSMSV2.run_cli()
