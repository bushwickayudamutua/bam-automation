from typing import NamedTuple, TypedDict


class AirtableRecord(NamedTuple):
    id: int
    phone_number: str


class InputEvent(TypedDict):
    FIELD_NAME: str
    NEW_VALUE: str
    PHONE_NUMBERS_TO_UPDATE: str
