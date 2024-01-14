import os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, List, NewType, Union


def list_files(path: str, ignore_hidden: bool = False) -> List[str]:
    f"""
    Recursively list files under a directory.
    :param path: A filepath as a string
    :param ignore_hidden: whether or not to ignore hidden files (starting with ``.``)
    :return list
    """
    return (
        os.path.join(dp, f)
        for dp, dn, fn in os.walk(get_full(path))
        for f in fn
        if not (f.startswith(".") and ignore_hidden)
        and not f.endswith(".DS_Store")
        and not dp == "__MACOSX"
    )


def get_full(path: str) -> str:
    f"""
    Get a full path
    :param path: A filepath as a string
    :return str
    """
    path = os.path.expandvars(path)
    path = os.path.expanduser(path)
    path = os.path.normpath(path)
    path = os.path.abspath(path)
    return path


def now_est():
    """
    Get the current time in EST
    :return datetime
    """
    return datetime.now(ZoneInfo("America/New_York"))


def to_list(value: Union[Any, List[Any]]) -> List[Any]:
    """
    Convert a value to a list
    :param value: A value
    :return list
    """
    if isinstance(value, list):
        return value
    return [value]
