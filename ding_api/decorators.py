from functools import wraps
from requests.exceptions import RequestException


def request_write_error_handler(err):
    with open("request_error.log", "a") as f:
        if not isinstance(err, str):
            f.write("err不是字符串")
        f.write("".join([err, "\r\n"]))


def ding_exc_cache(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            result = func(self, *args, **kwargs)
        except RequestException as e:
            request_write_error_handler(e)
            return None
        return result

    return wrapper
