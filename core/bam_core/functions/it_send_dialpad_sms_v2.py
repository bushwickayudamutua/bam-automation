from bam_core.lib.airtable_v2 import Household
from bam_core.functions.base import Function
from bam_core.functions.params import Params, Param
from bam_core.utils.etc import now_est, replace_parameters
from datetime import date
import json


MESSAGE_TEMPLATE_PARAMS = "sms_params/message_template.json"
REQUEST_LABEL_PARAMS = "sms_params/item_label.json"

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
            description="Name of the volunteer sending sms messages. Must be one value or a list matching the order of 'languages'",
        ),
        Param(
            name="message_template",
            type="json",
            default=None,
            description="Optional parameters to override default parameters for text messace scripts in 'sms_params/message_template.json'",
        ),
        Param(
            name="request_label",
            type="json",
            default=None,
            description="Optional parameters to override default parameters for handling EG item types in 'sms_params/request_label.json'",
        ),
        Param(
            name="formula_filter",
            type="string",
            default=None,
            description="An optional formula to filter the Households Airtable view.",
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
        message_template_custom = params.get("message_template")
        request_label_custom = params.get("request_label")
        formula_filter = params.get("formula_filter", None)
        exclude_texted_today = params.get("exclude_texted_today", True)
        max_messages = params.get("max_messages", 500)
        dry_run = params.get("dry_run", True)
        verbose = params.get("verbose", True)
        
        # Load default parameters for text messace scripts:
        with open(MESSAGE_TEMPLATE_PARAMS, 'r') as file:
            message_template_pars = json.load(file)

        # Load default parameters for handling EG item types:
        with open(REQUEST_LABEL_PARAMS, 'r') as file:
            request_label_pars = json.load(file)

        # Add / replace with custom input parameters:
        message_template_pars = replace_parameters(message_template_custom, message_template_pars)
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
                item_label = request_label_pars[item][lang]
                item_cap = request_label_pars["capitalize"]
                day = message_template_pars[lang][distro_day]["day"]
                time = message_template_pars[lang][distro_day]["time"]
                location = message_template_pars[lang]["location"]

                if not item_label:
                    ValueError(f"Item label can not be empty! Please provide label in {lang} with 'request_label'")

                if not all(day, time, location):
                    ValueError(f"Distro details can not be empty! Please provide day, time, and location in {lang} with 'message_template'")

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
        
        # Optional formula filtering:
        today = date.today().strftime("%Y-%m-%d")
        exclude_texted_today_formula = "NOT(IS_SAME({Last Texted}, '"+today+"'))"
        if formula_filter is not None and exclude_texted_today:
            households_formula = "AND("+formula_filter+", "+exclude_texted_today_formula+")"
        elif formula_filter is not None:
            households_formula = formula_filter
        elif exclude_texted_today:
            households_formula = exclude_texted_today_formula
        else:
            households_formula = None

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
            self.log.info(f"No households selected!")
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
        num_messages_sent = 0
        for household in self.dialpad.it_send_sms_v2(
            households=households,
            messages=messages,
            testing=dry_run,
            verbose=verbose
        ):
            if not household:
                continue

            num_messages_sent += 1

            # update last auto-texted field in Airtable
            if not dry_run:
                if verbose:
                    self.log.info(f"Setting Last Texted for household {household.bam_id} at {household.phone_number}")
                household.last_texted = now_est().date()
                household.save()

        self.log.info(f"Successfully {mode_str}ed {num_messages_sent} messages!")
        num_failed = num_households - num_messages_sent
        if num_failed > 0:
            self.log.info(f"{num_failed} messages failed!") 


if __name__ == "__main__":
    ItSendDialpadSMSV2().run_cli()

