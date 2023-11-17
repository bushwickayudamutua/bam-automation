from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pyairtable import Table, formulas as fx, Api

from bam_core import settings
from bam_core.constants import (
    AIRTABLE_DATETIME_FORMAT,
    EG_REQUESTS_FIELD,
    EG_STATUS_FIELD,
    PHONE_FIELD,
    ASSISTANCE_REQUESTS_TABLE_NAME,
    ESSENTIAL_GOODS_TABLE_NAME,
    VOLUNTEERS_TABLE_NAME,
    MESH_VIEW_NAME,
)


class Airtable(object):
    def __init__(
        self,
        base_id: str = settings.AIRTABLE_BASE_ID,
        token: str = settings.AIRTABLE_TOKEN,
    ):
        self.base_id = base_id
        self.token = token
        self.api = Api(token)

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
    ) -> Table:
        """
        Get a table object from the Airtable API
        :param table_name: The name of the table to get
        :return Table
        """
        return self.api.table(self.base_id, table_name).all(
            view=view_name, fields=fields
        )

    def get_view_count(
        self, table: str, view: str, fields: List[str] = [], unique=False
    ) -> int:
        """
        Get a table object from the Airtable API
        :param table_name: The name of the table to get
        :return Table
        """
        records = self.get_view(
            table_name=table, view_name=view, fields=fields
        )
        if unique and len(fields) and len(records):
            uniques = set()
            for r in records:
                rf = r.get("fields", {})
                unique_field = ""
                for f in fields:
                    if f not in rf:
                        continue
                    unique_field += str(rf[f])
                uniques.add(unique_field)
            return len(set(uniques))
        return len(records)

    # core table objects

    @property
    def assistance_requests(self) -> Table:
        return self.get_table(ASSISTANCE_REQUESTS_TABLE_NAME)

    @property
    def essential_goods(self) -> Table:
        return self.get_table(ESSENTIAL_GOODS_TABLE_NAME)

    @property
    def volunteers(self) -> Table:
        return self.get_table(VOLUNTEERS_TABLE_NAME)

    @property
    def mesh_requests(self):
        return self.get_view(
            ASSISTANCE_REQUESTS_TABLE_NAME,
            MESH_VIEW_NAME,
        )

    def filter_table(
        self,
        table: Union[str, Table],
        expressions: List[Any],
        match_any: bool = False,
        sort: List[str] = ["-Date Submitted"],
        fields=[],
    ):
        if isinstance(table, str):
            table = self.get_table(table)
        if not match_any:
            formula = fx.AND(*expressions)
        else:
            formula = fx.OR(*expressions)
        return table.all(formula=formula, sort=sort, fields=fields)

    def get_phone_number_to_requests_lookup(
        self,
        view: Optional[str] = None,
        formula=None,
        phone_number_field: str = PHONE_FIELD,
        fields: List[str] = [EG_REQUESTS_FIELD, EG_STATUS_FIELD],
        sort: List[str] = ["-Date Submitted"],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch records from the Assistance Requests table
        and return a lookup by phone number
        :param view: The optional name of the view to fetch records from
        :param formula: The optional formula to filter records by
        :return: A lookup by phone number
        """
        # ensure phone field is included
        if PHONE_FIELD not in fields:
            fields.append(PHONE_FIELD)
        kwargs = {"fields": fields, "sort": sort}
        if view:
            kwargs["view"] = view
        if formula:
            kwargs["formula"] = formula
        records = self.assistance_requests.all(**kwargs)
        lookup = defaultdict(list)
        for record in records:
            fields = record.pop("fields", {})
            phone_number = fields.get(phone_number_field, None)
            if not phone_number:
                continue
            record["createdTime"] = datetime.strptime(
                record["createdTime"], AIRTABLE_DATETIME_FORMAT
            )
            # add fields to record
            record.update(fields)
            lookup[phone_number].append(record)
        return lookup

    def get_requests_for_phone_number(
        self,
        phone_number: str,
        fields: List[str] = [PHONE_FIELD, EG_REQUESTS_FIELD, EG_STATUS_FIELD],
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Fetch all records from the Assistance Requests table for a single phone number
        """
        return self.get_phone_number_to_requests_lookup(
            formula=fx.FIND(fx.STR_VALUE(phone_number), fx.FIELD(PHONE_FIELD)),
            fields=fields,
            **kwargs
        ).get(phone_number, [])
