# TODO: fix this test.
import pytest

from bam_core.functions import dedupe_airtable_views
from bam_core.functions.dedupe_airtable_views import (
    convert_airtable_datestr_to_date,
    Record,
)
from bam_core import constants


earliest_airtable_record = {
    "id": 0,
    "fields": {
        "Phone Number": "1234567890",
        "Date Submitted": "2022-09-10T19:53:01.000Z",
        constants.FOOD_VIEWS[0]["status_field_name"]: [],
    },
}
phone, date_submitted, status = earliest_airtable_record["fields"].values()
earliest_record = Record(
    earliest_airtable_record["id"],
    phone,
    convert_airtable_datestr_to_date(date_submitted),
    status,
)

later_airtable_record = {
    "id": 1,
    "fields": {
        "Phone Number": "1234567890",
        "Date Submitted": "2022-10-10T19:53:01.000Z",
        constants.FOOD_VIEWS[0]["status_field_name"]: [],
    },
}
phone, date_submitted, status = later_airtable_record["fields"].values()
later_record = Record(
    later_airtable_record["id"],
    phone,
    convert_airtable_datestr_to_date(date_submitted),
    status,
)

latest_airtable_record = {
    "id": 2,
    "fields": {
        "Phone Number": "1234567890",
        "Date Submitted": "2022-11-10T19:53:01.000Z",
        constants.FOOD_VIEWS[0]["status_field_name"]: [],
    },
}
phone, date_submitted, status = latest_airtable_record["fields"].values()
latest_record = Record(
    latest_airtable_record["id"],
    phone,
    convert_airtable_datestr_to_date(date_submitted),
    status,
)

in_outreach_airtable_record = {
    "id": 3,
    "fields": {
        "Phone Number": "1234567890",
        "Date Submitted": "2022-11-10T19:53:01.000Z",
        constants.FOOD_VIEWS[0]["status_field_name"]: ["OUTREACH_FLAG"],
    },
}
phone, date_submitted, status = in_outreach_airtable_record["fields"].values()
in_outreach_record = Record(
    in_outreach_airtable_record["id"],
    phone,
    convert_airtable_datestr_to_date(date_submitted),
    status,
)


@pytest.fixture(autouse=True)
def mock_set_record_status_as_dupe(monkeypatch):
    def mock(*args, **kwargs):
        pass

    monkeypatch.setattr(
        dedupe_airtable_views, "set_record_status_as_dupe", mock
    )


def test_no_dedupe(monkeypatch):
    def mock_table_records(*args, **kwargs):
        records_with_no_dupe = [earliest_airtable_record]
        return records_with_no_dupe

    monkeypatch.setattr(dedupe_airtable_views.table, "all", mock_table_records)
    records_to_keep = dedupe_airtable_views.dedupe_view(
        constants.FOOD_VIEWS[0]
    )
    assert records_to_keep == {earliest_record.phone_number: earliest_record}


def test_one_dedupe_view(monkeypatch):
    def mock_table_records(*args, **kwargs):
        records_with_one_dupe = [
            earliest_airtable_record,
            later_airtable_record,
        ]
        return records_with_one_dupe

    monkeypatch.setattr(dedupe_airtable_views.table, "all", mock_table_records)
    records_to_keep = dedupe_airtable_views.dedupe_view(
        constants.FOOD_VIEWS[0]
    )
    assert records_to_keep == {earliest_record.phone_number: earliest_record}


def test_multiple_dedupe_view(monkeypatch):
    def mock_table_records(*args, **kwargs):
        records_with_multiple_dupes = [
            earliest_airtable_record,
            later_airtable_record,
            latest_airtable_record,
        ]
        return records_with_multiple_dupes

    monkeypatch.setattr(dedupe_airtable_views.table, "all", mock_table_records)
    records_to_keep = dedupe_airtable_views.dedupe_view(
        constants.FOOD_VIEWS[0]
    )
    assert records_to_keep == {earliest_record.phone_number: earliest_record}


# def test_dedupe_mesh_view(monkeypatch):
#     def mock_table_records(*args, **kwargs):
#         records_with_outreach = [
#             in_outreach_airtable_record,
#             earlier_airtable_record,
#             later_airtable_record,
#         ]
#         return records_with_outreach

#     monkeypatch.setattr(dedupe_views.air.assistance_requests, "all", mock_table_records)
#     records_to_keep = dedupe_airtable_views.dedupe_view(constants.MESH_VIEW)
#     assert records_to_keep == {in_outreach_record.phone_number: in_outreach_record}
