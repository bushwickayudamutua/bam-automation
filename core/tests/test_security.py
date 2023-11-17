from bam_core.settings import *


def test_no_secrets_are_published():
    # ensure that secrets are not published to the repo in settings files
    assert S3_ACCESS_KEY_ID is None
    assert S3_SECRET_ACCESS_KEY is None
    assert DO_TOKEN is None
    assert AIRTABLE_TOKEN is None
    assert AIRTABLE_BASE_ID is None
