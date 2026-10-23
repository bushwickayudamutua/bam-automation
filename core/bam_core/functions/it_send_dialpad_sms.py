import json
import logging
from enum import StrEnum
from pathlib import Path

import pyairtable.formulas as F
from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
    TypeAdapter,
    model_validator,
)

from bam_core.functions.base import Function
from bam_core.lib.airtable_v2 import Household
from bam_core.lib.dialpad import Dialpad
from bam_core.utils.etc import deep_merge, now_est

logger = logging.getLogger(__name__)
dialpad = Dialpad(parent_logger=logger)

DEFUALT_MESSAGE_TEMPLATE_CFG_PATH = "default_message_template_config.json"


class RequestKey(StrEnum):
    baby_diapers = "baby_diapers"
    adult_diapers = "adult_diapers"
    clothing = "clothing"
    soap = "soap"
    pads = "pads"
    school_supplies = "school_supplies"
    pots_and_pans = "pots_and_pans"
    plates_and_cups = "plates_and_cups"

    def to_airtable(self) -> str:
        if self == RequestKey.baby_diapers:
            return "Pañales / Baby Diapers / 嬰兒紙尿褲"
        if self == RequestKey.adult_diapers:
            return "Pañales de adultos / Adult Diapers / 成人紙尿褲"
        if self == RequestKey.clothing:
            return "Ropa / Clothing / 服裝"
        if self == RequestKey.soap:
            return "Jabón & Productos de baño / Soap & Shower Products / 肥皂和淋浴用品"
        if self == RequestKey.pads:
            return "Productos Femenino - Toallitas / Feminine Products - Pads / 衛生巾"
        if self == RequestKey.school_supplies:
            return "Cosas de Escuela / School Supplies / 學校用品"
        if self == RequestKey.pots_and_pans:
            return "Ollas y Sartenes / Pots & Pans / 鍋碗瓢盆"
        if self == RequestKey.plates_and_cups:
            return "Platos o Tazas / Plates or Cups / 盘子或杯子"


class LanguageKey(StrEnum):
    english = "english"
    spanish = "spanish"
    arabic = "arabic"
    mandarin = "mandarin"
    cantonese = "cantonese"
    toishanese = "toishanese"

    def to_airtable(self) -> str:
        if self == LanguageKey.english:
            return "Inglés / English / 英文"
        if self == LanguageKey.spanish:
            return "Español / Spanish / 西班牙语"
        if self == LanguageKey.arabic:
            return "Árabe / Arabic / 阿拉伯語"
        if self == LanguageKey.mandarin:
            return "Chino Mandarín / Mandarin / 普通话"
        if self == LanguageKey.cantonese:
            return "Chino Cantonés / Cantonese / 广东话"
        if self == LanguageKey.toishanese:
            return "Chino Toishanés / Toishanese / 台山话"


class DistroDescription(BaseModel):
    day: str
    time: str


class MessageTemplate(BaseModel):
    volunteer_name: str
    script: list[str]
    location: str
    request_labels: dict[RequestKey, str]
    distro: dict[str, DistroDescription]


class RequestLabel(BaseModel):
    types: list[str]
    translations: dict[str, str]


class ItSendDialpadSMS(Function):
    """
    Given an Airtable view, iterate over EG items and languages, and send SMS messages to phone numbers in the view via Dialpad.
    """

    distro_day: str = Field(
        description="The day of EG distro. Must be defined in 'message_template' for each language.",
    )
    request_types: list[RequestKey] = Field(
        description="The EG items to text for. The order determines which item will be mentioned in each message."
    )
    languages: list[LanguageKey] = Field(
        description="The languages to text in. The order determines language preference in the case of multilingual households.",
    )
    view_name: str | None = Field(
        None, description="An Airtable view name to fetch Household records from."
    )
    message_template_config_path: str | None = Field(
        None, description="Path to the template config file."
    )
    message_template_overrides: dict[LanguageKey, dict] | None = Field(
        None,
        description="Optional parameters to override default parameters for text message scripts.",
    )
    volunteer_name: str | None = Field(
        None,
        description="Name of the volunteer sending sms messages. This parameter takes precedence over any volunteer names specified in message_template_overrides.",
    )
    location: str | None = Field(
        None,
        description="Location of the distro. This parameters takes precedence over any locations specified in message_template_overrides.",
    )
    exclude_texted_today: bool = Field(
        True,
        description="If true, households that were texted today will be excluded.",
    )
    max_messages: int = Field(
        500,
        description="The maximum number of messages to send",
    )
    dry_run: bool = Field(
        True,
        description="If true, messages will not be sent. Useful for testing.",
    )
    verbose: bool = Field(
        True,
        description="If true, the sms message per household is logged.",
    )

    _message_template_map: dict[LanguageKey, MessageTemplate] = PrivateAttr()

    @model_validator(mode="after")
    def build_message_template_map(self):
        # Read config file
        if self.message_template_config_path is None:
            config_path = Path(__file__).parent / DEFUALT_MESSAGE_TEMPLATE_CFG_PATH
        else:
            config_path = self.message_template_config_path
        with open(config_path, "r") as f:
            message_template_map_obj = json.load(f)

        # Apply overrides
        message_template_map_obj = (
            message_template_map_obj
            if self.message_template_overrides is None
            else deep_merge(message_template_map_obj, self.message_template_overrides)
        )

        # Save volunteer name in config if provided
        if self.volunteer_name is not None:
            for template in message_template_map_obj.values():
                template["volunteer_name"] = self.volunteer_name

        # Save location in config if provided
        if self.location is not None:
            for template in message_template_map_obj.values():
                template["location"] = self.location

        # Validate object
        self._message_template_map = TypeAdapter(
            dict[LanguageKey, MessageTemplate]
        ).validate_python(message_template_map_obj)

        return self

    def run(self):
        # Pull Household records, applying appropriate filtering and sorting
        household_formulas = [
            # Filter by language
            F.OR(
                F.GT(
                    F.FIND(lang_key.to_airtable(), F.to_formula(Household.languages)),
                    0,
                )
                for lang_key in self.languages
            ),
            # Filter by open request type
            F.OR(
                F.GT(
                    F.FIND(
                        req_key.to_airtable(),
                        F.to_formula(Household.open_request_types),
                    ),
                    0,
                )
                for req_key in self.request_types
            ),
        ]
        today_date = now_est().date()
        if self.exclude_texted_today:
            # Filter out households texted today, if specified
            household_formulas.append(Household.last_texted.ne(today_date))

        households = Household.all(
            view=self.view_name, formula=F.AND(household_formulas)
        )

        households = sorted(
            households,
            key=lambda household: min(
                request_date
                for req_key in self.request_types
                if (request_date := household.get_requested_date(req_key.to_airtable()))
                is not None
            ),
        )

        households = households[: self.max_messages]

        logger.info(f"Selected {len(households)} household!")

        # Create text message per household:
        messages = []
        for household in households:
            message_template = next(
                message_template
                for lang_key, message_template in self._message_template_map.items()
                if lang_key.to_airtable() in household.languages
            )

            first_name = dialpad._get_first_word(household.name)
            volunteer_name = message_template.volunteer_name
            request_label = next(
                message_template.request_labels[req_key]
                for req_key in self.request_types
                if req_key.to_airtable() in household.open_request_types
            )
            day = message_template.distro[self.distro_day].day
            time = message_template.distro[self.distro_day].time
            location = message_template.location

            curr_script = "".join(
                [
                    first_name
                    if expr == "[FIRST_NAME]"
                    else volunteer_name
                    if expr == "[VOLUNTEER_NAME]"
                    else request_label
                    if expr == "[REQUEST_LABEL]"
                    else day
                    if expr == "[DAY]"
                    else time
                    if expr == "[TIME]"
                    else location
                    if expr == "[LOCATION]"
                    else expr
                    for expr in message_template.script
                ]
            )

            messages.append(curr_script)

        # Send SMS via Dialpad per household:
        num_messages_sent = dialpad.it_send_sms(
            households=households,
            messages=messages,
            today_date=today_date,
            testing=self.dry_run,
            verbose=self.verbose,
        )

        if not self.dry_run:
            logger.info(f"Successfully sent {num_messages_sent} messages!")
            num_failed = len(households) - num_messages_sent
            if num_failed > 0:
                logger.info(f"{num_failed} messages failed!")


if __name__ == "__main__":
    ItSendDialpadSMS.run_cli()
