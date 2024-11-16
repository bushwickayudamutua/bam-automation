from bam_core.lib.airtable import Airtable


def test_get_record_link():
    result = Airtable(base_id="1234")._get_record_link(
        "table_name", "record_id"
    )
    assert result == "https://airtable.com/1234/table_name/record_id"
