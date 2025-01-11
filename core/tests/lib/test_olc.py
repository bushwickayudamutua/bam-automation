from bam_core.lib import olc


def test_olc_encode():
    lat = 40.7128
    lng = -74.0060
    plus_code = olc.encode(lat, lng)
    assert plus_code == "87G7PX7V+"


def test_olc_encode_with_nulls():
    plus_code = olc.encode(None, 45.0)
    assert plus_code is None
