# -*- coding: UTF-8 -*-

import os
import sys
import time
import json
import random
import requests
from datetime import datetime
from collections import Counter
from pprint import pformat
from typing import Any, List, Dict, Optional, Iterator, Union

import click
import dotenv
import requests
from twilio.rest import Client


# Constants #

# credentials
dotenv.load_dotenv()

AIRTABLE_API_KEY = os.getenv("AIRTABLE_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_DEFAULT_PHONE_NUMBER = "+17185500340"
TWILIO_SMS_RESPONSE_PHONE_NUMBER = "+16468870083"
TWILIO_SMS_RESPONSE_FLOW_ID = "FW3f1b6b05fcbed803358a38e1fb981c25"

# airtable info


class Language:
    CANTONESE = "Cantonese"
    MANDARIN = "Mandarin"
    ENGLISH = "English"
    SPANISH = "Spanish"
    QUECHUA = "Quechua"
    ALL = "All"


# How to sort message text if contact's language is not provided
ALL_LANGUAGE_ORDER = [Language.SPANISH, Language.CANTONESE, Language.ENGLISH]


# Twilio Client


# retry with backoff helper
def retry_with_backoff(retries=5, backoff_in_seconds=5):
    def rwb(f):
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    if e.code == 21611:
                        if x == retries:
                            raise
                        else:
                            sleep = backoff_in_seconds * 2**x + random.uniform(
                                0, 1
                            )
                            time.sleep(sleep)
                            x += 1
                    else:
                        raise

        return wrapper

    return rwb


class Twilio:
    def __init__(self):
        self.client = Client(
            TWILIO_ACCOUNT_SID,
            TWILIO_AUTH_TOKEN,
        )
        self.errors = []

    @retry_with_backoff(retries=5)
    def send_text_message(
        self,
        to_phone_number,
        from_phone_number,
        content,
        sleep_time=0.1,
        **kwargs,
    ):
        try:
            return self.client.api.account.messages.create(
                to=f"+1{to_phone_number}",
                from_=from_phone_number,
                body=content,
            )
        except Exception as e:
            message = None
            if e.code == 21211:
                message = f"WARNING: Phone number {to_phone_number} is invalid. (https://www.twilio.com/docs/api/errors/21211)"
            elif e.code == 21610:
                message = f"WARNING: Phone number {to_phone_number} has unsubscribed. (https://www.twilio.com/docs/api/errors/21610)"
            elif e.code == 21408:
                message = f"WARNING: SMS has not been enabled for the region indicated by the number {to_phone_number}. (https://www.twilio.com/docs/errors/21408)"
            elif e.code == 21611:
                return "overflow"
            else:
                raise e
            if message:
                self.errors.append(
                    f"phone_number: {to_phone_number}, message: {message}"
                )
                print(message)
        time.sleep(sleep_time)

    def start_studio_flow(
        self,
        to_phone_number,
        from_phone_number,
        content,
        campaign_name,
        sleep_time=6,
        **kwargs,
    ):
        try:
            # set country
            to_phone_number = f"+1{to_phone_number}"
            execution = self.client.studio.flows(
                TWILIO_SMS_RESPONSE_FLOW_ID
            ).executions.create(
                to=to_phone_number,
                from_=from_phone_number,
                parameters={
                    "content": content,
                    "campaign_name": campaign_name,
                    "to_phone_number": to_phone_number,
                },
            )
        except Exception as e:
            self.errors.append(f"phone_number: {to_phone_number} message: {e}")
        time.sleep(sleep_time)


# Main Funcitons #


def fetch_airtable_records(
    airtable_url: str,
    airtable_view_name: str,
    filter_by_formula: Optional[str] = None,
) -> Iterator[Dict]:
    """
    Fetch a list of records for an Airtable View
    """
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    }
    params = {"view": airtable_view_name}
    if filter_by_formula:
        params["filterByFormula"] = filter_by_formula
    offset = ""
    while offset is not None:
        if offset:
            params["offset"] = offset
        response = requests.get(airtable_url, headers=headers, params=params)
        response.raise_for_status()
        payload = response.json()
        for record in payload["records"]:
            yield record.get("fields", {})
        offset = payload.get("offset")


def determine_message_language(
    contact_langauges: Union[List[str], str]
) -> str:
    """
    Given a list of a contact's languages, determine the langauge to send the message in.
    """
    # prefer string matching
    if isinstance(contact_langauges, list):
        contact_langauges = ",".join(contact_langauges)

    # Always prefer Spanish if a contact's list of languages includes it.
    if Language.SPANISH in contact_langauges:
        return Language.SPANISH

    # we only write messages in Spanish
    elif Language.QUECHUA in contact_langauges:
        return Language.SPANISH

    # we only write messages in Cantonese
    elif Language.MANDARIN in contact_langauges:
        return Language.CANTONESE

    elif Language.CANTONESE in contact_langauges:
        return Language.CANTONESE

    # Only send in English if a contact's list of languages doesn't include other languages
    elif Language.ENGLISH in contact_langauges:
        return Language.ENGLISH

    # Otherwise send the message in all languages
    return Language.ALL


def build_twilio_message(
    airtable_contact_record: Dict[str, Any],
    message_text_by_language: Dict[str, str],
    airtable_contact_language_field: str = "Language",
    airtable_contact_phone_number_field: str = "Phone number",
    template_variables: dict = {},
) -> Dict[str, Any]:
    """
    Given an airtable contact record and a dictionary of message text (from Airtable), build a twilio message.
    """
    contact_languages = airtable_contact_record.get(
        airtable_contact_language_field, []
    )
    message_language = determine_message_language(contact_languages)

    # never send a message without content
    message_content = message_text_by_language.get(message_language, None)

    # build a message with all available languages
    if message_content is None:
        message_content = "\n\n".join(
            [
                message_text_by_language.get(lang)
                for lang in ALL_LANGUAGE_ORDER
                if lang in message_text_by_language
            ]
        )
    # optionally add template varaibles
    if len(template_variables.keys()) > 0:
        message_content = message_content.format(**template_variables)
    return {
        "language": message_language,
        "content": message_content,
        "to_phone_number": airtable_contact_record.get(
            airtable_contact_phone_number_field
        ),
    }


def build_twilio_messages_for_contacts(
    airtable_contact_url: str,
    airtable_contact_view_name: str,
    airtable_text_message_url: str,
    airtable_text_message_view_name: str,
    airtable_text_message_name: str,
    airtable_contact_language_field: str = "Language",
    airtable_contact_phone_number_field: str = "Phone number",
    airtable_text_message_language_field: str = "Language",
    airtable_text_message_content_field: str = "Notes",
    template_variables: dict = {},
) -> Iterator[Dict[str, Any]]:
    """
    lookup list of contacts (phone number / language)
    lookup message text by language
    for each contact, build language-specific message. if no language specified on contact, use all languages
    send message via Twilio API, handling errors + backoff logic
    optionally perform above in "Dry-Run" mode
    """
    # fetch contact records
    contact_records = fetch_airtable_records(
        airtable_url=airtable_contact_url,
        airtable_view_name=airtable_contact_view_name,
    )

    # fetch text message content records
    text_message_records = list(
        fetch_airtable_records(
            airtable_url=airtable_text_message_url,
            airtable_view_name=airtable_text_message_view_name,
            filter_by_formula="{Name}='%s'" % airtable_text_message_name,
        )
    )

    # build a lookup of language to text message content
    message_text_by_language = {
        r.get(airtable_text_message_language_field): r.get(
            airtable_text_message_content_field
        )
        for r in text_message_records
    }

    for contact_record in contact_records:
        # ignore contacts without phone numbers
        if contact_record.get(airtable_contact_phone_number_field, "") == "":
            print(
                f"WARNING: no '{airtable_contact_phone_number_field}' field found for contact:\n{contact_record}"
            )
        else:
            yield build_twilio_message(
                contact_record,
                message_text_by_language,
                airtable_contact_language_field,
                airtable_contact_phone_number_field,
                template_variables,
            )


@click.command()
@click.option(
    "--airtable_contact_url",
    default="https://api.airtable.com/v0/appEiw5APdZSlOwdm/Mass%20Text%20List",
    help="The API Endpoint for the Table to pull the contact records from.",
    show_default=True,
)
@click.option(
    "--airtable_contact_view_name",
    help="The view which filters out just the Contacts to send this mass text to.",
    required=True,
)
@click.option(
    "--airtable_text_message_url",
    default="https://api.airtable.com/v0/appEiw5APdZSlOwdm/Language%20for%20Mass%20Texts",
    help="The API Endpoint for the Table to pull the message content (by langauge) from.",
    show_default=True,
)
@click.option(
    "--airtable_text_message_view_name",
    default="Language for Mass Texts",
    help="The view which filters out just the message content (by langauge) for this mass text.",
    show_default=True,
)
@click.option(
    "--airtable_text_message_name",
    help='The value of the "Name" field for the message content.',
    required=True,
)
@click.option(
    "--airtable_contact_language_field",
    default="Language",
    help="The name of the column in the Contact view which contains the list of the Contact's languages spoken.",
    show_default=True,
)
@click.option(
    "--airtable_contact_phone_number_field",
    default="Phone number",
    help="The name of the column in the Contact view which contains the the Contact's Phone number.",
    show_default=True,
)
@click.option(
    "--airtable_text_message_language_field",
    default="Language",
    help="The name of the column in the message content view which contains the language of the message.",
    show_default=True,
)
@click.option(
    "--airtable_text_message_content_field",
    default="Notes",
    help="The name of the column in the message content view which contains the content for the message.",
    show_default=True,
)
@click.option(
    "--airtable_contact_start_at",
    default=1,
    help="The index number of Contact Records list to start at. Useful when resuming a mass text which breaks midway.",
)
@click.option(
    "--campaign_name",
    default=f"SMS Response Tracker {datetime.now().strftime('%Y-%m-%d')}",
    help="The campaign name to store along responses when using the --capture_responses option.",
    show_default=True,
)
@click.option(
    "--template_variables",
    default="{}",
    type=str,
    help='JSON-formatted variables to pass into template strings in messages. Any string formatted {EXAMPLE} can be populated by passing \'{"EXAMPLE": "test"}\' at runtime.',
)
@click.option(
    "--capture_responses/--dont_capture_responses",
    default=False,
    help="Whether or not to send this message through the SMS Responses Tracker",
)
@click.option(
    "--send/--dont_send",
    default=False,
    help="Whether or not to send the text messages via Twilio's API",
)
def main(
    airtable_contact_url,
    airtable_contact_view_name,
    airtable_text_message_url,
    airtable_text_message_view_name,
    airtable_text_message_name,
    airtable_contact_language_field,
    airtable_contact_phone_number_field,
    airtable_text_message_language_field,
    airtable_text_message_content_field,
    airtable_contact_start_at,
    campaign_name,
    template_variables,
    capture_responses,
    send,
):
    twilio = Twilio()

    message_by_language_counter = Counter()
    message_counter = 0

    # load template variables
    try:
        template_variables = json.loads(template_variables)
    except json.JSONDecodeError:
        print(
            f"--template_variables must be a valid json string, was passed: {template_variables}"
        )
        sys.exit(1)

    # build the messages
    messages = build_twilio_messages_for_contacts(
        airtable_contact_url,
        airtable_contact_view_name,
        airtable_text_message_url,
        airtable_text_message_view_name,
        airtable_text_message_name,
        airtable_contact_language_field,
        airtable_contact_phone_number_field,
        airtable_text_message_language_field,
        airtable_text_message_content_field,
        template_variables,
    )
    try:
        for i, message in enumerate(messages, start=1):
            # optionally skipping x number of records.
            if i < airtable_contact_start_at:
                click.echo(f"({i}) Skipping Contact...")
                continue
            log_message = "\n\tLanguage: {language}\n\tMessage: {content}\n\tNumber: {to_phone_number}".format(
                **message
            )
            if send:
                if not capture_responses:
                    message["from_phone_number"] = TWILIO_DEFAULT_PHONE_NUMBER
                    click.echo(f"({i}) Sending...{log_message}")
                    response = twilio.send_text_message(**message)
                    if response == "overflow":
                        click.echo(
                            f"Stopping because queue is full. Restart at record {i}"
                        )
                        break
                else:
                    message[
                        "from_phone_number"
                    ] = TWILIO_SMS_RESPONSE_PHONE_NUMBER
                    message["campaign_name"] = campaign_name
                    click.echo(
                        f"({i}) Sending and waiting for response... {log_message}"
                    )
                    twilio.start_studio_flow(**message)
            else:
                click.echo(f" ({i}) Testing...{log_message}")

            message_counter += 1
            message_by_language_counter[message["language"]] += 1
    finally:
        click.echo(
            f"📲 Sent {message_counter} messages.\nBy language: {pformat(message_by_language_counter)}"
        )
        if len(twilio.errors):
            click.echo(
                "🙀 Got some errors:\n{errors}".format(
                    errors="\n".join(twilio.errors)
                )
            )


if __name__ == "__main__":
    main()
