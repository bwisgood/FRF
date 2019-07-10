import threading

from flask import jsonify, current_app


class BaseFRFException(Exception):
    def __init__(self, code, msg, *args, **kwargs):
        self.code = code
        self.msg = msg
        self.args = args
        self.kwargs = kwargs

    @classmethod
    def handle(cls):
        if not current_app.config.get("DEBUG"):
            return jsonify(code=5000, msg='未知内部错误', data=None)
        else:
            raise cls

    def __str__(self):
        return "[{}] {}".format(self.code, self.msg)


class ArgumentException(BaseFRFException):
    """
    传入参数错误
    """

    def __init__(self):
        super(ArgumentException, self).__init__(4002, "传入数据错误")


class AuthException(BaseFRFException):
    def __init__(self):
        super(AuthException, self).__init__(4004, "权限错误")


class DataAuthException(AuthException):
    """
    数据权限错误
    """


class RequestAuthException(AuthException):
    """
    请求权限错误
    """


default_accept_errors = [BaseFRFException, ArgumentException, AuthException, DataAuthException, RequestAuthException]


class FRFErrorHandler(object):
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(FRFErrorHandler, "_instance"):
            with FRFErrorHandler._instance_lock:
                if not hasattr(FRFErrorHandler, "_instance"):
                    FRFErrorHandler._instance = object.__new__(cls)
        return FRFErrorHandler._instance

    def __init__(self, accept_errors=None):
        self.accept_errors = default_accept_errors
        if accept_errors is not None:
            self.accept_errors.extend(accept_errors)
            pass

    def register_handler(self, app):
        for e in self.accept_errors:
            app.register_error_handler(e, e.handle)


if __name__ == '__main__':

    try:
        raise ArgumentException
    except Exception as e:
        print(e)
