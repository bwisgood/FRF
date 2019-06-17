class BaseFRFException(Exception):
    def __init__(self, code, msg, *args, **kwargs):
        self.code = code
        self.msg = msg
        self.args = args
        self.kwargs = kwargs

    def __str__(self):
        return "[{}] {}".format(self.code, self.msg)


class ArgumentException(BaseFRFException):
    """
    传入参数错误
    """

    def __init__(self):
        super(ArgumentException, self).__init__(4002, "传入数据错误")


class DataAuthException(BaseFRFException):
    """
    数据权限错误
    """

    def __init__(self):
        super(DataAuthException, self).__init__(4004, "数据权限错误")


if __name__ == '__main__':

    try:
        raise ArgumentException
    except Exception as e:
        print(e)
