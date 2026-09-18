"""
All things related to serialization / deserialization
This module should not import from other utils
"""

import json
from uuid import UUID
from decimal import Decimal
from inspect import isgenerator
from collections import Counter
import datetime
from typing import Any


# ///////////////////
# CLASSES
# ///////////////////


class SmartJSONEncoder(json.JSONEncoder):
    """JSON encoder extending Flask's default encoder to handle many different types"""

    item_separator = ","
    key_separator = ":"

    def default(self, o: Any) -> str:
        """Return a serializable for ``o``, or call the base implementation."""
        if isinstance(o, bytes):
            return o.decode("utf-8")
        if isinstance(o, Decimal):
            return float(o)
        if isinstance(o, (datetime.date, datetime.datetime, datetime.time)):
            return o.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        if isinstance(o, UUID):
            return str(o)
        if isinstance(o, set):
            return list(o)
        if isgenerator(o):
            return list(o)
        if isinstance(o, Counter):
            return dict(o)
        if self.refs and hasattr(o, "to_ref"):
            return o.to_ref()
        if hasattr(o, "to_dict"):
            return o.to_dict()
        if hasattr(o, "to_json"):
            return o.to_json()
        return json.JSONEncoder.default(self, o)


# ///////////////////
# FUNCTIONS
# ///////////////////


def json_to_obj(s: str) -> object:
    """
    json string > obj
    """
    return json.loads(s)


def obj_to_json(o: object) -> str:
    """
    obj > json string
    """
    return SmartJSONEncoder().encode(o)
