import os

PASSWORD_SALT = os.getenv("BAM_PASSWORD_SALT", "bam")
APIKEY = os.getenv("BAM_APIKEY", "bam")
DATABASE_URL = os.getenv("BAM_DATABASE_URL", "sqlite:///bam.db")
