import logging
import os
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)


def list_files(path: str, ignore_hidden: bool = False) -> list[str]:
    """
    Recursively list files under a directory.
    :param path: A filepath as a string
    :param ignore_hidden: whether or not to ignore hidden files (starting with ``.``)
    :return list
    """
    return [
        os.path.join(dp, f)
        for dp, _dn, fn in os.walk(get_full(path))
        for f in fn
        if not (f.startswith(".") and ignore_hidden)
        and not f.endswith(".DS_Store")
        and dp != "__MACOSX"
    ]


def get_full(path: str) -> str:
    """
    Get a full path
    :param path: A filepath as a string
    :return str
    """
    path = os.path.expandvars(path)
    path = os.path.expanduser(path)
    path = os.path.normpath(path)
    path = os.path.abspath(path)
    return path


def now_est() -> datetime:
    """
    Get the current time in EST
    :return datetime
    """
    return datetime.now(ZoneInfo("America/New_York"))


def now_utc() -> datetime:
    """
    Get the current time in UTC
    :return datetime
    """
    return datetime.now(ZoneInfo("UTC"))


def replace_parameters(
    A: dict,
    B: dict = None,
) -> dict:
    """
    Recursively adds named parameters from nested 'dict' A to B,
    and overrides existing values in B.
    """
    
    if B is None:
        B = deepcopy(A)
    else:
        for p, v in A.items():
            if isinstance(v, dict):
                B[p] = replace_parameters(v, B.get(p))
            else:
                B[p] = deepcopy(v)
    
    return B
