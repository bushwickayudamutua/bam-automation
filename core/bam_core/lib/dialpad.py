import csv
from typing import Any, Generator
import requests
import time
import random

from bam_core.settings import DIALPAD_API_TOKEN, DIALPAD_USER_ID

DIALPAD_API_URL = "https://dialpad.com/api/v2/sms"
BAM_URL = "https://bushwickayudamutua.com/"
MAX_MESSAGE_LENGTH = 160
RANDOM_REQUEST_URL_SIZE = (
    4  # Size of the random hex string to append to the URL
)


class Dialpad:
    def __init__(
        self,
        api_token=DIALPAD_API_TOKEN,
        user_id=DIALPAD_USER_ID,
        first_name_field="First Name",
        phone_number_field="Phone Number",
        logger=None,
    ):
        self.api_token = api_token
        self.user_id = user_id
        self.first_name_field = first_name_field  # Default field for first names, can be overridden
        self.phone_number_field = phone_number_field  # Default field for phone numbers, can be overridden
        self.log = logger

    def _show_parsing_warning(self, count):
        response = input(
            f"You're about to send {count} texts, are you super sure about the decision you're about to make? (y/n): "
        )
        return response.lower() == "y"

    def get_random_hex(self, size=4):
        return

    def _get_random_request_url(self):
        return BAM_URL + "".join(
            random.choices("0123456789abcdef", k=RANDOM_REQUEST_URL_SIZE)
        )

    def _clean_phone_number(self, phone_number):
        if not phone_number:
            return ""
        clean_number = "".join(filter(str.isdigit, phone_number))
        if len(clean_number) == 10:
            clean_number = "+1" + clean_number
        elif len(clean_number) == 11:
            clean_number = "+" + clean_number
        return clean_number

    def _get_first_word(self, s):
        if not s:
            return ""
        return s.strip().split()[0]

    def _split_message(self, message, max_length=MAX_MESSAGE_LENGTH):
        words = message.split(" ")
        split_messages = []
        current_message = ""
        for word in words:
            if len(current_message) + len(word) + 1 > max_length:
                split_messages.append(current_message.strip())
                current_message = word + " "
            else:
                current_message += word + " "
        if current_message.strip():
            split_messages.append(current_message.strip())
        return split_messages

    def send_sms(
        self, rows: list[dict[str, Any]], message: str, testing: bool = False
    ) -> Generator[dict[str, Any], None, None]:
        for i, row in enumerate(rows):
            if not testing and i % 30 == 0 and i != 0:
                self.log.info(
                    "Taking a little nap so that we don't get rate limited, will start back up in 30 seconds 😴"
                )
                time.sleep(30)
                self.log.info("Texts are sending, go to dialpad 🐥💼")

            request_url = self._get_random_request_url()
            first_name = self._get_first_word(
                row.get(self.first_name_field, "")
            )
            phone_num = self._clean_phone_number(
                row.get(self.phone_number_field, "")
            )

            updated_message = message.replace(
                "[FIRST_NAME]", first_name
            ).replace("[REQUEST_URL]", request_url)
            split_messages = self._split_message(updated_message)

            for current_split_message in split_messages:
                payload = {
                    "infer_country_code": False,
                    "to_numbers": phone_num,
                    "text": current_split_message,
                    "user_id": self.user_id,
                }
                headers = {
                    "accept": "application/json",
                    "content-type": "application/json",
                    "authorization": f"Bearer {self.api_token}",
                }
                self.log.info(
                    f"""[{phone_num}] {"WOULD SEND" if testing else "SENDING"}: '{current_split_message}'"""
                )
                if not testing:
                    try:
                        response = requests.post(
                            DIALPAD_API_URL, json=payload, headers=headers
                        )
                        json_resp = response.json()
                        self.log.info(f"Response: {json_resp}")
                        if not response.ok:
                            api_error_message = json_resp.get("error", {}).get(
                                "message", "Unknown error"
                            )
                            self.log.error(
                                f"Error sending message to {first_name} at {phone_num}: {api_error_message}"
                            )
                            break
                    except Exception as e:
                        self.log.error(f"Error: {e}")
            if not testing:
                time.sleep(2)
            yield row

    def send_sms_from_csv(self, file_path, user_message):
        with open(file_path, newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)
            print(f"{len(rows)} records in this file")
            if self._show_parsing_warning(len(rows)):
                for row in self.send_sms(rows, user_message):
                    pass
            else:
                print("Operation cancelled.")


if __name__ == "__main__":
    dialpad = Dialpad()
    dialpad.send_sms_from_csv(
        "contacts.csv",
        "Hello [FIRST_NAME], visit [REQUEST_URL] for more info!",
    )
