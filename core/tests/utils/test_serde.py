from bam_core.utils.serde import obj_to_json


def test_obj_to_json():
    assert obj_to_json({"a": 1}) == '{"a":1}'
