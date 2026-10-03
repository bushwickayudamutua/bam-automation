from pathlib import Path
import json
from pyairtable.formulas import AND, OR
from pydantic import BaseModel, TypeAdapter

from bam_core.functions.base import Function
from bam_core.functions.params import Param, Params
from bam_core.lib.airtable_v2 import Request, Household
from bam_core.settings import EG_DISTRO_LOCATION
from bam_core.utils.etc import now_est


class MessageConfig(BaseModel):
    template: str
    day: dict[str, str]
    request_type: dict[str, str]

message_configs_adapter = TypeAdapter(dict[str, MessageConfig])


class SendEgDistroTextBlast(Function):
    """
    Given a list of EG request types and a list of languages, send SMS messages to the oldest households requesting any such items and speaking any of those languages.
    """

    params = Params(
        Param(
            name="req_types",
            type="string_list",
            required=True,
            description="A list of request types to send texts for. The priority is determined by the order of this list. If you are using the default message template path, must be one of the values in the Type column of the Requests table.",
        ),
        Param(
            name="languages",
            type="string_list",
            required=True,
            description="A list of languages to send texts for. The priority is determined by the order of the list. If you are using the default message template path, must be one of the values in the Language column of the Households table.",
        ),
        Param(
            name="volunteer_name",
            type="string",
            required=True,
            description="The name of the volunteer sending texts.",
        ),
        Param(
            name="day",
            type="string",
            required=True,
            description="The day of the week the distro is on. If you are using the default message template path, must be one of 'su', 'mo', 'tu', 'we', 'th', 'fr', 'sa'.",
        ),
        Param(
            name="address",
            type="string",
            default=None,
            description="The address of the distro event. If no address is provided, the usual location will be used.",
        ),
        Param(
            name="max_messages",
            type="int",
            default=500,
            description="The maximum number of messages to send. If not specified, all records across all the views will be processed.",
        ),
        Param(
            name="message_config_path",
            type="string",
            default=None,
            description="The path to the message config used for message templating and translation. If no path is provided, the internal one will be used. Not configurable in DigitalOcean.",
        ),
        Param(
            name="dry_run",
            type="bool",
            default=True,
            description="If true, messages will not be sent and only logged. Useful for testing.",
        ),
    )

    def _get_primary_language(
        self, household: Household, languages: list[str]
    ) -> str | None:
        for language in languages:
            if language in household.languages:
                return language

    def _get_primary_request_type(
        self, household: Household, request_types: list[str]
    ) -> str | None:
        for request_type in request_types:
            if request_type in household.open_request_types:
                return request_type

    def _write_message(
        self,
        *,
        name: str,
        message_config: MessageConfig,
        request_type: str,
        volunteer_name: str,
        day: str,
        address: str,
    ) -> str:
        message_template = message_config.template

        request_type_label = message_config.request_type.get(request_type)
        if request_type_label is None:
            raise RuntimeError(f"Unable to translate request type: {request_type}")

        day_label = message_config.day.get(day)
        if day_label is None:
            raise RuntimeError(f"Unable to translate day: {day}")

        return (
            message_template.replace("[FIRST_NAME]", name)
            .replace("[REQUEST_TYPE]", request_type_label)
            .replace("[VOLUNTEER_NAME]", volunteer_name)
            .replace("[DAY]", day_label)
            .replace("[ADDRESS]", address)
        )

    def run(self, params):
        """
        Send Dialpad text blast for essential goods distro
        """
        # Load and validate params
        req_types: list[str] = params.get("req_types")
        languages: list[str] = params.get("languages")
        volunteer_name: str = params.get("volunteer_name")
        day: str = params.get("day")
        address: str | None = params.get("address")
        max_messages: int = params.get("max_messages", 500)
        message_config_path: str = params.get("message_template_path", "dialpad_translation_templates.json")
        dry_run: bool = params.get("dry_run", True)

        if len(req_types) == 0:
            self.log.info("No request types provided")
            return

        if len(languages) == 0:
            self.log.info("No languages provided")
            return

        if address is None:
            if EG_DISTRO_LOCATION is None:
                raise RuntimeError("Missing required environment variable: EG_DISTRO_LOCATION")
            address = EG_DISTRO_LOCATION

        message_configs = message_configs_adapter.validate_json(Path(message_config_path).read_text())

        # Write messages
        messages = {}
        for request in Request.all(
            formula=AND(Request.status.eq("Open"), OR(*[Request.type.eq(req_type) for req_type in req_types])),
            sort=[Request.request_opened_at.field_name],
        ):
            household = request.household
            if household is None:
                self.log.warning(f"Encountered request with empty household value: {request.id}")
                continue

            if household.id in messages:
                continue

            primary_language = self._get_primary_language(household, languages)
            if primary_language is None:
                continue

            primary_request_type = self._get_primary_request_type(household, req_types)
            if primary_request_type is None:
                # Should never happen
                continue

            try:
                messages[household] = self._write_message(
                    name=household.name,
                    message_config=message_configs[primary_language],
                    request_type=primary_request_type,
                    volunteer_name=volunteer_name,
                    day=day,
                    address=address,
                )
            except RuntimeError as e:
                self.log.error(f"Failed to write message for household {household.id}: {e}")
                return

            if len(messages) >= max_messages:
                break

        # Send messages to Dialpad
        for household in self.dialpad.send_sms_v3(
            list(messages.items()),
            testing=dry_run,
        ):
            # update last auto-texted field in Airtable
            if not dry_run:
                self.log.info(f"Setting Last Texted for household {household.bam_id}")
                household.last_texted = now_est().date()
                household.save()


if __name__ == "__main__":
    SendDialpadSMSV2().run_cli()
