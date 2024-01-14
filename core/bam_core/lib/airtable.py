from collections import defaultdict
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional, Union

from pyairtable import Table, formulas as fx, Api

from bam_core import settings
from bam_core.utils.etc import to_list
from bam_core.constants import (
    AIRTABLE_DATETIME_FORMAT,
    PHONE_FIELD,
    ASSISTANCE_REQUESTS_TABLE_NAME,
    FULFILLED_REQUESTS_TABLE_NAME,
    ESSENTIAL_GOODS_TABLE_NAME,
    VOLUNTEERS_TABLE_NAME,
    MESH_VIEW_NAME,
    REQUESTS_SCHEMA,
    REQUEST_FIELDS,
)


log = logging.getLogger(__name__)


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
    def fulfilled_requests(self) -> Table:
        return self.get_table(FULFILLED_REQUESTS_TABLE_NAME)

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

    @classmethod
    def _flatten_record(cls, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten an Airtable record
        """
        fields = record.pop("fields", {})
        record.update(fields)
        return record

    def get_phone_number_to_requests_lookup(
        self,
        view: Optional[str] = None,
        formula=None,
        phone_number_field: str = PHONE_FIELD,
        fields: List[str] = REQUEST_FIELDS,
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
            record = self._flatten_record(record)
            phone_number = record.get(phone_number_field, None)
            if not phone_number:
                continue
            record["createdTime"] = datetime.strptime(
                record["createdTime"], AIRTABLE_DATETIME_FORMAT
            )
            lookup[phone_number].append(record)
        return lookup

    def get_requests_for_phone_number(
        self,
        phone_number: str,
        fields: List[str] = REQUEST_FIELDS,
        **kwargs,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all records from the Assistance Requests table for a single phone number
        """
        return self.get_phone_number_to_requests_lookup(
            formula=fx.FIND(fx.STR_VALUE(phone_number), fx.FIELD(PHONE_FIELD)),
            fields=fields,
            **kwargs,
        ).get(phone_number, [])

    ##############################
    # Request Analysis Functions #
    ##############################

    @classmethod
    def _perform_request_analysis(
        cls,
        analysis: Dict[str, Any],
        request_field: str,
        request_tag: str,
        status_tags: List[str],
        delivered_tags: List[str],
        timeout_tags: List[str],
        invalid_tags: List[str],
        missed_tag: Optional[str] = None,
    ):
        """
        Perform analysis of requests for a single request tag
        """
        # DELIVERED
        if any([dt in status_tags for dt in delivered_tags]):
            analysis[request_field]["delivered"].append(request_tag)
        # TIMEOUT
        elif any([tt in status_tags for tt in timeout_tags]):
            analysis[request_field]["timeout"].append(request_tag)
        # INVALID
        elif any([it in status_tags for it in invalid_tags]):
            analysis[request_field]["invalid"].append(request_tag)
        # MISSED
        elif missed_tag and missed_tag in status_tags:
            analysis[request_field]["missed"].append(request_tag)
            # missed appointments are still open
            analysis[request_field]["open"].append(request_tag)
        # OPEN
        else:
            analysis[request_field]["open"].append(request_tag)
        return analysis

    @classmethod
    def analyze_requests(
        cls, record: Dict[str, Any], requests_schema=REQUESTS_SCHEMA
    ) -> Dict[str, List[str]]:
        """
        Get open requests (not completed nor timed-out) and completed requests from a record.
        NOTE: The record must contain the fields specified in REQUESTS_SCHEMA.
              To get all necessary fields, you can pass all REQUEST_FIELDS into the fields parameter of the Airtable API.
        """

        # flatten record
        record = cls._flatten_record(record)

        analysis = defaultdict(lambda: defaultdict(list))

        for schema in requests_schema:
            request_field = schema["request_field"]
            status_field = schema["status_field"]
            request_tags = record.get(request_field, [])
            status_tags = record.get(status_field, [])
            item_schema = schema["items"]

            for request_tag in request_tags:
                request_tag_schema = item_schema.get(request_tag, None)

                if not request_tag_schema:
                    log.debug(
                        f"Unknown request tag '{request_tag}' for field '{request_field}'"
                    )
                    continue

                delivered_tags = to_list(
                    request_tag_schema.get("delivered", [])
                )
                timeout_tags = to_list(request_tag_schema.get("timeout", []))
                invalid_tags = to_list(request_tag_schema.get("invalid", []))
                missed_tag = request_tag_schema.get("missed", None)
                sub_item_schema = request_tag_schema.get("items", None)

                if not sub_item_schema:
                    analysis = cls._perform_request_analysis(
                        analysis,
                        request_field,
                        request_tag,
                        status_tags,
                        delivered_tags,
                        timeout_tags,
                        invalid_tags,
                        missed_tag,
                    )

                else:
                    ########################
                    # One level of nesting #
                    ########################

                    # handle nested requests
                    sub_request_field = sub_item_schema["request_field"]
                    sub_status_field = sub_item_schema["status_field"]
                    sub_request_tags = record.get(sub_request_field, [])
                    sub_status_tags = record.get(sub_status_field, [])

                    for sub_request_tag in sub_request_tags:
                        sub_request_tag_schema = sub_item_schema["items"].get(
                            sub_request_tag, None
                        )
                        if not sub_request_tag_schema:
                            log.debug(
                                f"Unknown request tag '{sub_request_tag}' for field '{sub_request_field}'"
                            )
                            continue

                        sub_delivered_tags = to_list(
                            sub_request_tag_schema.get("delivered", [])
                        )
                        sub_timeout_tags = to_list(
                            sub_request_tag_schema.get("timeout", [])
                        )
                        sub_invalid_tags = to_list(
                            sub_request_tag_schema.get("invalid", [])
                        )
                        sub_missed_tag = sub_request_tag_schema.get(
                            "missed", None
                        )

                        sub_sub_item_schema = sub_request_tag_schema.get(
                            "items", None
                        )

                        if not sub_sub_item_schema:
                            analysis = cls._perform_request_analysis(
                                analysis,
                                sub_request_field,
                                sub_request_tag,
                                sub_status_tags,
                                sub_delivered_tags,
                                sub_timeout_tags + timeout_tags,
                                sub_invalid_tags,
                                sub_missed_tag,
                            )

                        else:
                            #########################
                            # Two levels of nesting #
                            #########################

                            # handle doubly nested requests
                            sub_sub_request_field = sub_sub_item_schema[
                                "request_field"
                            ]
                            sub_sub_status_field = sub_sub_item_schema[
                                "status_field"
                            ]
                            sub_sub_request_tags = record.get(
                                sub_sub_request_field, []
                            )
                            sub_sub_status_tags = record.get(
                                sub_sub_status_field, []
                            )

                            for sub_sub_request_tag in sub_sub_request_tags:
                                sub_sub_request_tag_schema = (
                                    sub_sub_item_schema["items"].get(
                                        sub_sub_request_tag, None
                                    )
                                )
                                if not sub_sub_request_tag_schema:
                                    log.debug(
                                        f"Unknown request tag '{sub_sub_request_tag}' for field '{sub_sub_request_field}'"
                                    )
                                    continue

                                sub_sub_delivered_tags = to_list(
                                    sub_sub_request_tag_schema.get(
                                        "delivered", []
                                    )
                                )
                                sub_sub_timeout_tags = to_list(
                                    sub_sub_request_tag_schema.get(
                                        "timeout", []
                                    )
                                )
                                sub_sub_invalid_tags = to_list(
                                    sub_sub_request_tag_schema.get(
                                        "invalid", []
                                    )
                                )
                                sub_sub_missed_tag = (
                                    sub_sub_request_tag_schema.get(
                                        "missed", None
                                    )
                                )

                                analysis = cls._perform_request_analysis(
                                    analysis,
                                    sub_sub_request_field,
                                    sub_sub_request_tag,
                                    sub_sub_status_tags,
                                    # respect delivered tags from one level up (only relevant for Beds)
                                    sub_delivered_tags
                                    + sub_sub_delivered_tags,
                                    sub_sub_timeout_tags
                                    + sub_timeout_tags
                                    + timeout_tags,
                                    sub_sub_invalid_tags,
                                    sub_sub_missed_tag,
                                )

        return analysis
