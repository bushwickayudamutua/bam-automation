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
            name="request_types",
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
        Param(
            name="verbose",
            type="bool",
            default=True,
            description="If true, the sms message per household is logged.",
        ),
    )

    def run(self, params, context):
        """
        Snapshot Airtable tables
        """
        view_name = params.get("view_name")
        distro_day = params.get("distro_day")
        request_types = params.get("request_types")
        languages = params.get("languages")
        volunteer = params.get("volunteer")
        message_template_yaml = params.get("message_template")
        item_label_yaml = params.get("item_label")
        exclude_texted_today = params.get("exclude_texted_today", True)
        max_messages = params.get("max_messages", 500)
        dry_run = params.get("dry_run", True)
        verbose = params.get("verbose", True)

        with open(message_template_yaml, 'r') as file:
            message_template_pars = yaml.safe_load(file)

        with open(item_label_yaml, 'r') as file:
            item_label_pars = yaml.safe_load(file)

        # Create message templates iterating over 'request_types' and 'languages':
        message_template = {}
        for item in request_types:
            message_template[item] = {}
            for lang, vol in zip(languages, volunteer):
                item_label = item_label_pars[item][lang]
                item_cap = item_label_pars["capitalize"]
                day = message_template_pars[lang][distro_day]["day"]
                time = message_template_pars[lang][distro_day]["time"]
                location = message_template_pars[lang]["location"]
                curr_msg = message_template_pars[lang]["script"]
                if lang == "Arabic":
                    curr_msg = (
                        curr_msg
                        .replace("[متطوع]", vol)
                        .replace("[المنتج]", item_label)
                        .replace("[يوم]", day)
                        .replace("[وقت]", time)
                        .replace("[مكان]", location)
                    )
                else:
                    if item_cap and lang in ["English", "Spanish"]:
                        item_label = item_label.upper()
                    curr_msg = (
                        curr_msg
                        .replace("[VOLUNTEER]", vol)
                        .replace("[ITEM_LABEL]", item_label)
                        .replace("[DAY]", day)
                        .replace("[TIME]", time)
                        .replace("[LOCATION]", location)
                    )
                message_template[item][lang] = curr_msg
        
        households_formula = "NOT(IS_SAME({Last Texted}, TODAY()))" if exclude_texted_today else None
        households = Household.all(view=view_name, formula=households_formula)

        for item in request_types:
            item_label_pars[item]["types"] = set(item_label_pars[item]["types"])

        for lang in languages:
            message_template_pars[lang]["languages"] = set(message_template_pars[lang]["languages"])

        # Create text message per household:
        messages = []
        for household in households:
            curr_name = household.name

            which_type = [
                i for i, item in enumerate(request_types)
                if item_label_pars[item]["types"].issubset(set(household.open_request_types))
            ]
            if which_type:
                curr_type = request_types[which_type[0]]
            else:
                messages.append(None)
                continue

            which_lang = [
                i for i, lang in enumerate(languages)
                if message_template_pars[lang]["languages"].issubset(set(household.languages))
            ]
            if which_lang:
                curr_lang = languages[which_lang[0]]
            else:
                messages.append(None)
                continue

            curr_msg = message_template[curr_type][curr_lang]
            curr_msg = curr_msg.replace("[FIRST_NAME]", curr_name) # this is not possible in Arabic yet
            messages.append(curr_msg)

        selected_households = [m is not None for m in messages]
        households = households[selected_households]
        messages = messages[selected_households]
        
        self.log.info(f"Selected {len(households)} households!")

        # Send SMS via Dialpad per household:
        num_messages_sent = 0
        for household in self.dialpad.it_send_sms_v2(
            households=households,
            message=messages,
            testing=dry_run,
            verbose=verbose
        ):
            if not household:
                continue

            num_messages_sent += 1
            if num_messages_sent >= max_messages:
                break

            # update last auto-texted field in Airtable
            if not dry_run:
                if verbose:
                    self.log.info(f"Setting Last Texted for household {household.bam_id}")
                household.last_texted = now_est().date()
                household.save()

        self.log.info(f"Successfully sent {num_messages_sent} messages!")
        num_failed = len(households) - num_messages_sent
        if num_failed > 0:
            self.log.info(f"{num_failed} messages failed!") 


if __name__ == "__main__":
    ItSendDialpadSMSV2().run_cli()
