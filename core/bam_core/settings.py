import os
import dotenv
import logging
import logging.config
import json
import base64

# load .env file
dotenv.load_dotenv()

AIRTABLE_TOKEN = os.getenv("BAM_AIRTABLE_TOKEN", None)
AIRTABLE_BASE_ID = os.getenv("BAM_AIRTABLE_BASE_ID", None)
AIRTABLE_ASSISTANCE_REQUESTS_TABLE_ID = os.getenv(
    "BAM_AIRTABLE_ASSISTANCE_REQUESTS_TABLE_ID", None
)
AIRTABLE_VOLUNTEERS_TABLE_ID = os.getenv(
    "BAM_AIRTABLE_VOLUNTEERS_TABLE_ID", None
)
AIRTABLE_ESSENTIAL_GOODS_DONATIONS_TABLE_ID = os.getenv(
    "BAM_AIRTABLE_ESSENTIAL_GOODS_DONATIONS_TABLE_ID", None
)

# mailjet settings
MAILJET_API_KEY = os.getenv("BAM_MAILJET_API_KEY", None)
MAILJET_API_SECRET = os.getenv("BAM_MAILJET_API_SECRET", None)

# google settings
GOOGLE_MAPS_API_KEY = os.getenv("BAM_GOOGLE_MAPS_API_KEY", None)
GOOGLE_SERVICE_ACCOUNT_CONFIG = json.loads(
    base64.b64decode(
        os.getenv("BAM_GOOGLE_SERVICE_ACCOUNT_JSON_BASE64", "e30=")
    )
)

# s3 settings
DO_TOKEN = os.getenv("BAM_DO_TOKEN", None)
S3_BASE_URL = os.getenv(
    "BAM_S3_BASE_URL", "https://nyc3.digitaloceanspaces.com"
)
S3_ENDPOINT_URL = os.getenv(
    "BAM_S3_ENDPOINT_URL", "https://nyc3.digitaloceanspaces.com"
)
S3_ACCESS_KEY_ID = os.getenv("BAM_S3_ACCESS_KEY_ID", None)
S3_SECRET_ACCESS_KEY = os.getenv("BAM_S3_SECRET_ACCESS_KEY", None)
S3_BUCKET = os.getenv("BAM_S3_BUCKET", "bam-file")
S3_REGION_NAME = os.getenv("BAM_S3_REGION_NAME", "nyc3")
S3_PLATFORM = os.getenv("BAM_S3_PLATFORM", "do")
S3_CDN_ID = os.getenv("BAM_S3_CDN_ID", None)

# logging settings
LOG_LEVEL = os.getenv("BAM_LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv(
    "BAM_LOG_FORMAT",
    r"[%(levelname)s] -> %(message)s",
)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": True,
    "formatters": {"default": {"format": (LOG_FORMAT), "datefmt": "%H:%M:%S"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": LOG_LEVEL,
            "formatter": "default",
        }
    },
    "root": {"level": LOG_LEVEL, "handlers": ["console"]},
}

logging.config.dictConfig(LOGGING_CONFIG)
