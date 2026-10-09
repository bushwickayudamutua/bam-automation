from bam_core.lib.airtable_v2 import Household
from bam_core.functions.base import Function
from bam_core.functions.params import Params, Param, ItSMSMessageTemplateParams, ItSMSRequestLabelParams
from bam_core.utils.etc import now_est, replace_parameters
from argparse import ArgumentParser
import json


class ItSendDialpadSMS(Function):
    """
    Given an Airtable view, iterate over EG items and languages, and send SMS messages to phone numbers in the view via Dialpad.
    """

    MESSAGE_TEMPLATE_PARAMS = "sms_params/message_template.json"
    REQUEST_LABEL_PARAMS = "sms_params/request_label.json"

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
            description="The EG items to text for. Must be defined in 'request_label' for each language.",
        ),
        Param(
            name="languages",
            type="string_list",
            required=True,
            description="The languages to text in. Must be included in 'request_label' and 'message_template' parameters.",
        ),
        Param(
            name="volunteer",
            type="string_list",
            required=True,
            description="Name of the volunteer sending sms messages. Must be one value (used for every language) or a list matching the order of 'languages'",
        ),
        Param(
            name="message_template",
            type="it_sms_message_template",
            default=None,
            description="Optional parameters to override default parameters for text message scripts in 'sms_params/message_template.json'",
        ),
        Param(
            name="request_label",
            type="it_sms_request_label",
            default=None,
            description="Optional parameters to override default parameters for handling EG item types in 'sms_params/request_label.json'",
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
        view_name = params.get("view_name")
        distro_day = params.get("distro_day")
        request_types = params.get("request_types")
        languages = params.get("languages")
        volunteer = params.get("volunteer")
        message_template_custom = params.get("message_template")
        request_label_custom = params.get("request_label")
        exclude_texted_today = params.get("exclude_texted_today", True)
        max_messages = params.get("max_messages", 500)
        dry_run = params.get("dry_run", True)
        verbose = params.get("verbose", True)
        
        # Load default parameters for text message scripts:
        with open(self.MESSAGE_TEMPLATE_PARAMS, 'r') as file:
            message_template_pars = ItSMSMessageTemplateParams().validate(json.load(file))

        # Load default parameters for handling EG item types:
        with open(self.REQUEST_LABEL_PARAMS, 'r') as file:
            request_label_pars = ItSMSRequestLabelParams().validate(json.load(file))

        # Add / replace with custom input parameters:
        if message_template_custom:
            message_template_pars = replace_parameters(message_template_custom, message_template_pars)
        if request_label_custom:
            request_label_pars = replace_parameters(request_label_custom, request_label_pars)
        
        if len(volunteer) == 1:
            volunteer = volunteer * len(languages)
        elif len(volunteer) != len(languages):
            raise ValueError("'volunteer' must be one value or a list matching the order of 'languages'!")

        # Create message templates iterating over 'request_types' and 'languages':
        message_template = {}
        for item in request_types:
            message_template[item] = {}
            for lang, vol in zip(languages, volunteer):
                request_label = request_label_pars[item][lang]
                item_cap = request_label_pars["capitalize"]
                location = message_template_pars[lang]["location"]
                day = message_template_pars[lang]["distro"][distro_day]["day"]
                time = message_template_pars[lang]["distro"][distro_day]["time"]

                curr_msg = message_template_pars[lang]["script"]
                if lang == "Arabic":
                    curr_msg = (
                        curr_msg
                        .replace("[متطوع]", vol)
                        .replace("[المنتج]", request_label)
                        .replace("[يوم]", day)
                        .replace("[وقت]", time)
                        .replace("[مكان]", location)
                    )
                else:
                    if item_cap and lang in ["English", "Spanish"]:
                        request_label = request_label.upper()
                    curr_msg = (
                        curr_msg
                        .replace("[VOLUNTEER]", vol)
                        .replace("[REQUEST_LABEL]", request_label)
                        .replace("[DAY]", day)
                        .replace("[TIME]", time)
                        .replace("[LOCATION]", location)
                    )
                message_template[item][lang] = curr_msg

        # Pull records from the Households view (and exclude last texted today by default):
        today_date = now_est().date()
        households_formula = Household.last_texted.ne(today_date) if exclude_texted_today else None
        households = Household.all(view=view_name, formula=households_formula)

        # Create text message per household:
        messages = []
        for household in households:
            which_type = [
                i for i, item in enumerate(request_types)
                if all([rtype in household.open_request_types for rtype in request_label_pars[item]["types"]])
            ]
            if which_type:
                curr_type = request_types[which_type[0]]
            else:
                messages.append(None)
                continue

            which_lang = [
                i for i, lang in enumerate(languages)
                if any([hlang in household.languages for hlang in message_template_pars[lang]["languages"]])
            ]
            if which_lang:
                curr_lang = languages[which_lang[0]]
            else:
                messages.append(None)
                continue
            
            curr_msg = message_template[curr_type][curr_lang]
            curr_name = self.dialpad._get_first_word(household.name)
            if curr_lang == "Arabic":
                curr_msg = curr_msg.replace("[اسم]", curr_name)
            else:
                curr_msg = curr_msg.replace("[FIRST_NAME]", curr_name)
            
            messages.append(curr_msg)

        # Sort selected households by earliest requested date fields:
        households_idx = [i for i, m in enumerate(messages) if m is not None]
        request_dates = []
        for item in request_types:
            sort_type = request_label_pars[item]["types"][0]
            request_dates.append([
                d[0] if (d := households[i].get_requested_date(sort_type)) else "9999"
                for i in households_idx
            ])
        request_dates.append(households_idx)
        request_dates = sorted(zip(*request_dates))
        households_idx = [row[-1] for row in request_dates]

        # Restrict number of households if needed:
        num_households = len(households_idx)
        mode_str = "test" if dry_run else "text"
        if num_households == 0:
            self.log.info("No households selected!")
            return
        elif num_households > max_messages:
            households_idx = households_idx[:max_messages]
            self.log.info(f"Will {mode_str} {max_messages} out of {num_households} selected households!")
            num_households = max_messages
        else:
            self.log.info(f"Will {mode_str} {num_households} selected households!")
        
        households = [households[i] for i in households_idx]
        messages = [messages[i] for i in households_idx]

        # Send SMS via Dialpad per household:
        num_messages_sent = self.dialpad.it_send_sms(
            households=households,
            messages=messages,
            today_date=today_date,
            testing=dry_run,
            verbose=verbose
        )

        if dry_run:
            self.log.info("Successful dry run!")
        else:
            self.log.info(f"Successfully sent {num_messages_sent} messages!")
            num_failed = num_households - num_messages_sent
            if num_failed > 0:
                self.log.info(f"{num_failed} messages failed!")


    def run_cli(self):
        """
        The CLI handler, with optional '--config-file' in DO input format
        """
        config_parser = ArgumentParser(add_help=False)
        config_parser.add_argument("--config-file")
        config_args, other_args = config_parser.parse_known_args()

        if config_args.config_file is None:
            self.parser.add_argument("--config-file", help="JSON file of parameters in DO input format. Can not be combined with other arguments.")
            return super().run_cli()
        if other_args:
            raise ValueError("'--config-file' can not be combined with other arguments!")

        with open(config_args.config_file, "r") as file:
            return self.run_api(json.load(file))


if __name__ == "__main__":
    ItSendDialpadSMS().run_cli()

