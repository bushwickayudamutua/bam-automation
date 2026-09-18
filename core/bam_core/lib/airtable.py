from urllib3 import Retry
from typing import Any, Dict, List, Optional, Union

from pyairtable import Table, formulas as fx, Api

from bam_core import settings
from bam_core.constants import ESSENTIAL_GOODS_TABLE_NAME, VOLUNTEERS_TABLE_NAME


class Airtable(object):
    def __init__(
        self,
        base_id: str = settings.AIRTABLE_BASE_ID,
        token: str = settings.AIRTABLE_TOKEN,
        retry_strategy: bool | Retry | None = None,
    ):
        self.base_id = base_id
        self.token = token
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
        fields: List[str] = [],
        flatten: bool = False,
    ) -> Table:
        """
        Get a table object from the Airtable API
        :param table_name: The name of the table to get
        :return Table
        """
        records = self.api.table(self.base_id, table_name).all(
            view=view_name, fields=fields
        )
        if not flatten:
            return records

        # flatten records
        flattened_records = []
        for record in records:
            record = self._flatten_record(record)
            flattened_records.append(record)
        return flattened_records

    # core table objects

    @property
    def essential_goods(self) -> Table:
        return self.get_table(ESSENTIAL_GOODS_TABLE_NAME)

    @property
    def volunteers(self) -> Table:
        return self.get_table(VOLUNTEERS_TABLE_NAME)

    @classmethod
    def _flatten_record(cls, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten an Airtable record
        """
        fields = record.pop("fields", {})
        record.update(fields)
        return record
