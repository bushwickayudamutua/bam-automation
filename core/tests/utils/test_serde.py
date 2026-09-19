from bam_core.utils.serde import json_to_obj, obj_to_json


def test_obj_to_json():
    assert obj_to_json({"a": 1}) == '{"a":1}'


def test_json_to_obj():
    assert json_to_obj('{"a": 1}') == {"a": 1}
