"""
All things related to serialization / deserialization
This module should not import from other utils
"""

import datetime
import json
from decimal import Decimal
from inspect import isgenerator
from typing import Any
from uuid import UUID

# ///////////////////
# CLASSES
# ///////////////////


class SmartJSONEncoder(json.JSONEncoder):
    """JSON encoder extending Flask's default encoder to handle many different types"""

    item_separator = ","
    key_separator = ":"

    def default(self, o: Any) -> Any:
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
        return super().default(o)


# ///////////////////
# FUNCTIONS
# ///////////////////


def obj_to_json(o: object) -> str:
    """
    obj > json string
    """
    return SmartJSONEncoder().encode(o)
