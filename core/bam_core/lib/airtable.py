from typing import Any

from pyairtable import Api, Table
from pyairtable.api.types import RecordDict
from urllib3 import Retry

from bam_core.constants import ESSENTIAL_GOODS_TABLE_NAME, VOLUNTEERS_TABLE_NAME
from bam_core.settings import AIRTABLE_BASE_ID, AIRTABLE_TOKEN


class Airtable:
    def __init__(
        self,
        base_id: str | None = AIRTABLE_BASE_ID,
        token: str | None = AIRTABLE_TOKEN,
        retry_strategy: bool | Retry | None = None,
    ):
        if base_id is None:
            if AIRTABLE_BASE_ID is None:
                raise RuntimeError(
                    "Missing required environment variable: AIRTABLE_BASE_ID"
                )
            base_id = AIRTABLE_BASE_ID
        if token is None:
            if AIRTABLE_TOKEN is None:
                raise RuntimeError(
                    "Missing required environment variable: AIRTABLE_TOKEN"
                )
            token = AIRTABLE_TOKEN

        self.base_id = base_id
        self.api = Api(token, retry_strategy=retry_strategy)

    def get_table(self, table_name: str) -> Table:
        """
        Get a table object from the Airtable API
        :param table_name: The name of the table to get
        :return Table
        """
        return self.api.table(self.base_id, table_name)

    def get_view(
        self,
        table_name: str,
        view_name: str,
        fields: list[str] = [],
    ) -> list[RecordDict]:
        """
        Get a table object from the Airtable API
        :param table_name: The name of the table to get
        :return Table
        """
        return self.api.table(self.base_id, table_name).all(
            view=view_name, fields=fields
        )

    # core table objects

    @property
    def essential_goods(self) -> Table:
        return self.get_table(ESSENTIAL_GOODS_TABLE_NAME)

    @property
    def volunteers(self) -> Table:
        return self.get_table(VOLUNTEERS_TABLE_NAME)

    @classmethod
    def _flatten_record(cls, record: dict[str, Any]) -> dict[str, Any]:
        """
        Flatten an Airtable record
        """
        fields = record.pop("fields", {})
        record.update(fields)
        return record
