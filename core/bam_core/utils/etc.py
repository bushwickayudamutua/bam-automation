import os
import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, List, NewType, Union

log = logging.getLogger(__name__)


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


def to_list(value: Union[Any, List[Any]]) -> List[Any]:
    """
    Convert a value to a list
    :param value: A value
    :return list
    """
    if isinstance(value, list):
        return value
    return [value]


def to_bool(val: Union[str, bool]) -> bool:
    """
    Convert a string representation of truth to true or false.
    True values are 'y', 'yes', 't', 'true', 'on', and '1'
    False values are 'n', 'no', 'f', 'false', 'off', and '0'.
    Raises ValueError if 'val' is anything else.
    :param val: A value
    :return bool
    """
    if isinstance(val, bool):
        return val
    val = str(val).lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError("Invalid boolean value: %r" % (val,))


def retry(
    times: int = 5,
    wait: int = 5,
    backoff: float = 1.5,
    exceptions: List[Exception] = [Exception],
) -> Any:
    """
    Retry Decorator
    Retries the wrapped function/method `times` times if the exceptions listed
    in ``exceptions`` are thrown
    :param times: The number of times to repeat the wrapped function/method
    :param wait: The number of seconds to wait before retrying
    :param backoff: The backoff factor
    :param Exceptions: Lists of exceptions that trigger a retry attempt
    :return Any
    """

    def decorator(func):
        def new_fn(*args, **kwargs):
            attempt = 0
            while attempt < times:
                try:
                    return func(*args, **kwargs)
                except tuple(exceptions) as e:
                    attempt += 1
                    wait_time = wait * (backoff**attempt)
                    log.warning(
                        f"Exception thrown when attempting to run {func}: {e}."
                        f" Attempt {attempt} of {times}."
                        f" Waiting {wait_time} seconds before retrying."
                    )
                    time.sleep(wait_time)
            # If we've exhausted all attempts, raise the last exception
            raise e

        return new_fn

    return decorator
