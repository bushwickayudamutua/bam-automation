"""
All things related to serialization / deserialization
This module should not import from other utils
"""

import csv
import io
import gzip
import zlib
import json
import pickle
from uuid import UUID
from decimal import Decimal
from inspect import isgenerator
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List, Union

import yaml


# ///////////////////
# CLASSES
# ///////////////////


class SmartJSONEncoder(json.JSONEncoder):
    """JSON encoder extending Flask's default encoder to handle many different types"""

    item_separator = ","
    key_separator = ":"

    def default(self, obj: Any) -> str:
        """Return a serializable for ``o``, or call the base implementation."""
        if isinstance(obj, bytes):
            return obj.decode("utf-8")
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, (datetime.date, datetime.datetime, datetime.time)):
            return obj.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, set):
            return list(obj)
        if isgenerator(obj):
            return list(obj)
        if isinstance(obj, Counter):
            return dict(obj)
        if self.refs and hasattr(obj, "to_ref"):
            return obj.to_ref()
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "to_json"):
            return obj.to_json()
        return json.JSONEncoder.default(self, obj)


# ///////////////////
# FUNCTIONS
# ///////////////////


def file_to_gz(infile, outfile=None):
    """
    gzip a file
    """
    if not outfile:
        outfile = infile + ".gz"
    with gzip.open(outfile, "wb") as f_gz:
        with open(infile, "rb") as f_norm:
            f_gz.write(f_norm.read())


def gz_to_file(infile, outfile):
    """
    un-gzip a file
    """
    if not outfile:
        outfile = infile.replace(".gz", "")
    with gzip.open(infile, "rb") as f_gz:
        with open(outfile, "wb") as f_norm:
            f_gz.write(f_norm.read())


def str_to_gz_fobj(s: str) -> io.BytesIO:
    """
    string > gzip fobj
    """
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="w") as f:
        f.write(s)
    return out


def str_to_gz(s: str) -> bytes:
    """
    string > gzip bytes
    """
    return str_to_gz_fobj(s).getvalue()


def gz_to_str_fobj(b: bytes) -> io.BytesIO:
    """
    gzip > string
    """
    fileobj = io.BytesIO(b)
    return gzip.GzipFile(fileobj=fileobj, mode="r")


def gz_to_str(b: bytes) -> str:
    """
    gzip > str
    """
    f = gz_to_str_fobj(b)
    s = f.read()
    f.close()
    return s


def json_to_obj(s: Any) -> object:
    """
    json string > obj
    """
    # check for existing objects
    if isinstance(s, (dict, list)):
        return s
    return json.loads(s)


def obj_to_json(o: object) -> str:
    """
    obj > json string
    """
    return SmartJSONEncoder().encode(o)


def jsongz_to_obj(b: bytes) -> object:
    """
    json.gz > obj
    """
    return json_to_obj(gz_to_str(b))


def obj_to_jsongz(o: object) -> bytes:
    """
    obj > json.gz
    """
    return str_to_gz(obj_to_json(o))


def obj_to_jsongz_fobj(o: object) -> io.BytesIO:
    """
    obj > json.gz BytesIO
    """
    return str_to_gz_fobj(obj_to_json(o))


def pickle_to_obj(s: str) -> object:
    """
    pickle > obj
    """
    return pickle.loads(s)


def obj_to_pickle(o: object) -> str:
    """
    obj > pickle
    """
    return pickle.dumps(o)


def picklegz_to_obj(b: bytes) -> object:
    """
    pickle.gz > obj
    """
    return pickle_to_obj(gz_to_str(b))


def obj_to_picklegz(o: object) -> bytes:
    """
    obj > pickle.gz
    """
    return str_to_gz(obj_to_pickle(o))


def obj_to_picklegz_fobj(o: object) -> io.BytesIO:
    """
    obj > pickle.gz
    """
    return str_to_gz_fobj(obj_to_pickle(o))


def str_to_zip(s: str) -> bytes:
    """
    string > zip
    """
    if not isinstance(s, bytes):
        s = s.encode("utf-8")
    return zlib.compress(s)


def zip_to_str(b: bytes) -> str:
    """
    zip > string
    """
    return zlib.decompress(b)


def obj_to_yaml(o: object) -> str:
    """
    obj > yaml string
    """
    return yaml.dumps(o)


def yaml_to_obj(s: str) -> object:
    """
    yaml string > obj
    """
    return yaml.safe_load(s)


def obj_to_csv(o: List[Dict[str, Any]]) -> str:
    """
    obj > csv string
    """
    fieldnames = list(o[0].keys())
    fileobj = io.StringIO()
    writer = csv.DictWriter(
        fileobj,
        fieldnames=fieldnames,
        quotechar='"',
        quoting=csv.QUOTE_ALL,
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(o)
    csv_string = fileobj.getvalue()
    return csv_string


def csv_to_obj(s: str) -> List[Dict[str, Any]]:
    """
    csv string > obj
    """
    fileobj = io.StringIO(s)
    reader = csv.DictReader(fileobj)
    return [row for row in reader]


SERIALIZERS = {
    "json.gz": obj_to_jsongz,
    "json": obj_to_json,
    "pickle": obj_to_pickle,
    "pickle.gz": obj_to_picklegz,
    "zip": str_to_zip,
    "yaml": obj_to_yaml,
}

DESERIALIZERS = {
    "json.gz": jsongz_to_obj,
    "json": json_to_obj,
    "pickle": pickle_to_obj,
    "pickle.gz": picklegz_to_obj,
    "zip": zip_to_str,
    "yaml": yaml_to_obj,
}


def loads(s: Union[str, bytes], codec: str) -> object:
    """
    Serialize a string into a python object
    param s: a string or bytearray to load
    """
    if not codec in SERIALIZERS:
        raise NotImplementedError(f"[loads] Codec {codec} not supported")
    return SERIALIZERS.get(codec)(s)


def dumps(o: object, codec: str) -> Union[str, bytes]:
    """
    Serialize a string into a python object
    """
    if not codec in DESERIALIZERS:
        raise NotImplementedError(f"[dumps] Codec {codec} not supported")
    return DESERIALIZERS.get(codec)(o)
