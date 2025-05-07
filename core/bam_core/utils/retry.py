import time
import functools


def retry(attempts=5, wait=1, backoff=2):
    """
    A generic retry decorator.

    Args:
        attempts (int): Number of retry attempts.
        wait (float): Initial waiting time between attempts in seconds.
        backoff (float): Factor by which the wait time increases after each failure.

    Returns:
        function: The wrapped function with retry logic.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_wait = wait
            while attempt < attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt >= attempts:
                        raise
                    time.sleep(current_wait)
                    current_wait *= backoff

        return wrapper

    return decorator
