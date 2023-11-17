"""
Utilities for interacting with AWS S3 / Digital Ocean Spaces
"""
import os
from io import BytesIO
import tempfile
import logging
import urllib
from typing import Callable, List, Union, Optional

import boto3
import requests

from bam_core import settings
from bam_core.utils import etc

log = logging.getLogger(__name__)

BAM_STOR_DEFAULT_MIMETYPE = "binary/octet-stream"


def get_bucket_name_and_scheme(s3_url):
    """
    Get the bucket name and scheme from a s3 url
    """
    p = urllib.parse.urlparse(s3_url)
    if p.netloc == "":
        return p.scheme, p.path.split("/")[0]
    return p.scheme, p.netloc


def parse(s3_url) -> tuple:
    """
    Parse a s3 url into a bucket name and key
    :param s3_url: The s3 url
    :return tuple
    """
    scheme, bucket_name = get_bucket_name_and_scheme(s3_url)
    s3_prefix = f"{scheme}://{bucket_name}"
    if s3_url.startswith(s3_prefix):
        key = s3_url[len(s3_prefix) :]
    elif s3_url.startswith(bucket_name):
        key = s3_url[len(bucket_name) + 1 :]
    else:
        key = s3_url
    if key.startswith("/"):
        key = key[1:]
    return bucket_name, key


class S3(object):
    def __init__(
        self,
        bucket_name: str = settings.S3_BUCKET,
        aws_access_key_id: str = settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key: str = settings.S3_SECRET_ACCESS_KEY,
        endpoint_url: str = settings.S3_ENDPOINT_URL,
        base_url: str = settings.S3_BASE_URL,
        region_name: Optional[str] = settings.S3_REGION_NAME,
        platform: str = settings.S3_PLATFORM,
    ):
        self.scheme, self.bucket_name = get_bucket_name_and_scheme(bucket_name)
        self.access_key = aws_access_key_id
        self.access_secret = aws_secret_access_key
        self.endpoint_url = endpoint_url
        self.base_url = base_url
        self.region_name = region_name
        self.platform = platform
        self.resource = self.connect_resource()
        self.client = self.connect_client()
        self.bucket = self.get_bucket()
        if not self.scheme:
            self.scheme = "s3"
        if self.platform == "s3":
            self.scheme = "s3"
        self.s3_prefix = f"{self.scheme}://{self.bucket_name}/"

    # ////////////////////////
    #  Absolute Key Formatting
    #  (Allow all keys to have full s3:// paths on input and force full paths on output)
    # ///////////////////////

    def _in_key(self, key: str) -> str:
        f"""
        Format input key to accept full paths.
        :param key: An S3 key
        :return str
        """
        if key.startswith(self.s3_prefix):
            key = key.replace(self.s3_prefix, "")
        return key

    def _out_key(self, key: str) -> str:
        f"""
        Format output key to return full paths.
        :param key: An S3 key
        :return str
        """
        if not key.startswith(self.s3_prefix):
            key = f"{self.s3_prefix}{key}"
        return key

    def ensure(self) -> bool:
        """
        Ensure this bucket exists, return True if does, False if we create it
        """
        response = self.client.list_buckets()
        for bucket in response.get("Buckets", []):
            if bucket["Name"] == self.bucket_name:
                return True
        self.client.create_bucket(Bucket=self.bucket_name)
        return False

    # ////////////////////////
    #  Boto Client / Resource Connections
    # ///////////////////////
    @property
    def connection_kwargs(self):
        return dict(
            region_name=self.region_name,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.access_secret,
            endpoint_url=self.endpoint_url,
        )

    def connect_resource(self):
        """
        Connect to boto3 s3 resource
        """
        return boto3.resource("s3", **self.connection_kwargs)

    def connect_client(self):
        """
        Connect to boto3 s3 resource
        """
        return boto3.client("s3", **self.connection_kwargs)

    def get_bucket(self):
        """
        Get boto3 bucket object
        """
        return self.resource.Bucket(self.bucket_name)

    # ////////////////////////
    #  Core Methods
    # ///////////////////////

    def get_meta(self, key: str) -> dict:
        f"""
        Fetch metadata about this file on S3.
        :param key: An S3 key
        :return dict
        """
        return self.client.head_object(
            Bucket=self.bucket_name, Key=self._in_key(key)
        )

    def get_contents(self, key: set):
        f"""
        Fetch the file contents from a key.
        :param key: An S3 key
        :return dict
        """
        obj = self.resource.Object(self.bucket_name, self._in_key(key))
        return obj.get()["Body"].read()

    def exists(self, key: str) -> bool:
        f"""
        Check whether this key exists
        :param key: An S3 key
        :return bool
        """
        objs = list(self.bucket.objects.filter(Prefix=self._in_key(key)))
        if len(objs) > 0 and objs[0].key == self._in_key(key):
            return True
        return False

    def download(self, key: str, local_path: Union[None, str] = None) -> str:
        f"""
        Download an s3 key to a local file
        :param key: An S3 key
        :param local_path: The local filepath to write to. if it doesn't exist, the file will be written to a tempfile and the path will be outputted."
        :return str
        """
        if local_path is None:
            local_path = os.path.join(
                tempfile.mkdtemp(), os.path.basename(key)
            )
        self.bucket.download_file(self._in_key(key), local_path)
        return local_path

    def download_file_obj(
        self, key: str, fobj: Optional[BytesIO] = None
    ) -> BytesIO:
        f"""
        Download an s3 key to a file-like object
        :param key: An S3 key
        :param fobj: A file-like object to write to. If not provided, the function will create an `io.BytesIO` object, write the file contents to it, and return it.
        :return BytesIO
        """
        fobj = BytesIO()
        self.client.download_fileobj(self.bucket_name, self._in_key(key), fobj)
        return fobj

    def download_all(
        self,
        prefix: str,
        local_path: Union[None, str] = None,
        key_filter: Callable = lambda x: True,
    ):
        f"""
        Download s3 files under a given prefix to a local directory. Returns the list of local filepaths.
        :param prefix: A prefix used to identify a list of s3 keys
        :param local_path: The local filepath to write to. if it doesn't exist, the file will be written to a tempfile and the path will be outputted."
        :param key_filter: A function that accepts a key and returns true if we should include the key in the results
        :yield str
        """
        if local_path is None:
            local_path = tempfile.gettempdir(prefix="bam_")
        os.makedirs(local_path, exist_ok=True)

        for key in self.list_keys(prefix, key_filter):
            dl_path = os.path.join(local_path, os.path.basename(key))
            self.bucket.download_file(self._in_key(key), dl_path)
            yield dl_path

    def upload_file_obj(
        self, fobj: BytesIO, key: str, mimetype: Optional[str] = None
    ) -> None:
        f"""
        Upload a file object to s3, optionally setting its mimetype
        :param key: An S3 key
        :param fobj: A file-like object to write to. If not provided, the function will create an `io.BytesIO` object, write the file contents to it, and return it.
        :return None
        """
        self.bucket.upload_fileobj(
            fobj,
            self._in_key(key),
            ExtraArgs={
                "ContentType": mimetype or BAM_STOR_DEFAULT_MIMETYPE,
                "MetadataDirective": "REPLACE",
            },
        )

    def _upload_file(
        self, local_path: str, key: str, mimetype: BAM_STOR_DEFAULT_MIMETYPE
    ) -> str:
        f"""
        Upload a file to a s3 bucket, optionally applying a mimetype
        :param local_path: The local filepath to write to. if it doesn't exist, the file will be written to a tempfile and the path will be outputted."
        :param key: An S3 key
        :param mimetype: The mimetype to set for this key
        :return str
        """
        self.bucket.upload_file(
            local_path,
            self._in_key(key),
            ExtraArgs={"ContentType": mimetype},
        )
        return self._out_key(key)

    def upload(
        self, local_path: str, key: str, mimetype: BAM_STOR_DEFAULT_MIMETYPE
    ):
        f"""
        Upload a file to a s3 bucket
        :param local_path: The local filepath to write to. if it doesn't exist, the file will be written to a tempfile and the path will be outputted."
        :param key: An S3 key
        :param mimetype: The mimetype to set for this key
        :return str
        """
        # TODO: replace all these os calls with ``path```
        if os.path.isdir(local_path):
            log.debug(
                "[upload] found directory at {local_path}. The default is to recursively upload from here."
            )
            for filename in etc.list_files(local_path):
                sub_path = os.path.relpath(filename, start=local_path)
                file_key = os.path.join(key, sub_path)
                log.debug(f" [s3-upload] UPLOADING {filename} to {file_key}")
                self._upload_file(
                    filename,
                    file_key,
                )

        return self._upload_file(local_path, key, mimetype)

    def delete(self, key: str) -> None:
        f"""
        Delete a file from s3.
        :param key: An S3 key
        :return None
        """
        obj = self.bucket.Object(self._in_key(key))
        obj.delete()

    def move(self, old_key: str, new_key: str, copy: bool = False) -> str:
        f"""
        Move a file on s3
        :param old_key: the file's current location
        :param new_key: the file's new location
        :param copy: whether or not to leave current file where it is.
        :return str
        """
        new_obj = self.bucket.Object(self._in_key(new_key))
        new_obj.copy(
            {"Bucket": self.bucket_name, "Key": self._in_key(old_key)},
            ExtraArgs={"MetadataDirective": "REPLACE"},
        )

        if not copy:
            old_obj = self.bucket.Object(self._in_key(old_key))
            old_obj.delete()
        return self._out_key(old_key)

    def move_all(
        self, old_pfx: str, new_pfx: str, copy: bool = False
    ) -> List[str]:
        f"""
        Move files on s3 returning their new paths
        :param old_pfx: the files' current prefix
        :param new_key: the files' new prefix
        :param copy: whether or not to leave current files where they are.
        :return list
        """
        new_paths = []
        for old_obj in self.bucket.objects.filter(Prefix=self.in_key(old_pfx)):
            new_key = old_obj.key.replace(old_pfx, new_pfx, 1)
            new_obj = self.bucket.Object(self._in_key(new_key))
            new_obj.copy(
                {"Bucket": self.bucket_name, "Key": old_obj.key},
                ExtraArgs={"MetadataDirective": "REPLACE"},
            )
            # cleanup
            if not copy:
                old_obj.delete()
            new_paths.append(self._out_key(new_key))
        return new_paths

    def copy(self, old_key: str, new_key: str) -> None:
        """"""
        return self.move(
            self._in_key(old_key), self._in_key(new_key), copy=True
        )

    def copy_all(self, old_pfx: str, new_pfx: str) -> List[str]:
        """"""
        return self.move_all(
            self._in_key(old_pfx), self._in_key(new_pfx), copy=True
        )

    def list_keys(self, prefix: str, key_filter: Callable = lambda x: True):
        f"""
        List keys in S3 bucket.
        :param prefix: A prefix used to identify a list of s3 keys
        :param prefix: A function that accepts a key and returns true if we should include the key in the results
        :yield str
        """
        return (
            self._out_key(obj.key)
            for obj in self.bucket.objects.filter(Prefix=self._in_key(prefix))
            if key_filter(obj.key)
        )

    # ////////////////////////
    #  Public/Private Access
    # ///////////////////////

    def set_acl(
        self, key: str, acl: str, raise_on_missing: bool = False
    ) -> None:
        f"""
        Set the access control for a s3 key
        :param key: An S3 key
        :param acl: The ACL string (either ``private`` or ``public-read``)
        :param raise_on_missing: Whether or not to raise an error if the key does not exist
        :return None
        """
        if not self.exists(key):
            if raise_on_missing:
                raise ValueError(f"{key} does not exist in {self.s3_prefix}")
            return
        obj = self.bucket.Object(self._in_key(key))
        obj.Acl().put(ACL=acl)

    def set_private(self, key: str) -> None:
        f"""
        Make this file on s3 private
        :param key: An S3 key
        :return None
        """
        self.set_acl(key, "private")

    def set_public(self, key: str):
        f"""
        Make this file on s3 private
        :param key: An S3 key
        :return None
        """
        self.set_acl(key, "public-read")

    def get_presigned_url(self, key: str, expiration: int = 3600) -> str:
        f"""
        Create a presigned url for an s3 asset.
        :param key: An S3 key
        :param expiration: The number of seconds this url is valid for.
        :return str
        """
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": self._in_key(key)},
            ExpiresIn=expiration,
        )

    def get_public_url(self, key: str) -> str:
        f"""
        Get the public url for an s3 asset.
        :param key: An S3 key
        :return str
        """
        return "{}/{}/{}".format(
            self.client.meta.endpoint_url, self.bucket_name, self._in_key(key)
        )

    def purge_cdn_cache(self, prefix=""):
        """
        curl -X DELETE -H "Content-Type: application/json" \
        -H "Authorization: Bearer $API_TOKEN" \
        -d '{"files": ["*"]}' \
        "https://api.digitalocean.com/v2/cdn/endpoints/<CDN_ENDPOINT_ID>/cache"
        """
        r = requests.delete(
            f"https://api.digitalocean.com/v2/cdn/endpoints/{settings.S3_CDN_ID}/cache",
            headers={"Authorization": "Bearer {}".format(settings.DO_TOKEN)},
            json={"files": [f"{prefix}*"]},
        )
        r.raise_for_status()
        return True
