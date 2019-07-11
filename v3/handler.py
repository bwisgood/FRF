from functools import wraps

from flask import jsonify, request, g
from flask.views import MethodView

from .exceptions import ArgumentException, DataAuthException, RequestAuthException

from .response_code import RET
from .query import DataQuery
from .response_code import error_map


def request_wrapper(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # view级别的权限处理
        # 返回成功True或失败False
        if self.request_auth:
            if not self.request_auth():
                raise RequestAuthException
        try:
            # 这里处理传入参数
            self.dispatch_before_request()
            # 这里写查询和序列化将返回的结果交给下一个
            # view级别的数据参数处理
            if self.data_auth:
                if not self.data_auth(self):
                    raise DataAuthException
            result = func(self, *args, **kwargs)
            # 这里包装返回的参数
            result = self.dispatch_after_request(result)
        except Exception as e:
            if self.local_error_handler:
                return self.local_error_handler(e)
            else:
                raise e
        return result

    return wrapper


class ApiView(MethodView):
    serializer = None
    auth_class = []
    # query_set 如果想要用请求上下文的话需要传递一个函数来延迟实例化
    query_set = None
    pk_field = "id"
    paginate_field = ("page_num", "size", "error")

    look_up = ()
    like_fields = None
    order_by_fields = None
    query_cls = DataQuery

    request_auth = None
    data_auth = None
    local_error_handler = None

    add_g_data = True

    @staticmethod
    def empty_response():
        return jsonify(code=RET.NODATA, msg='没有数据', data=None)

    def __init__(self):
        # 继承父类的初始化方法
        # super().__init__(data)
        super(ApiView, self).__init__()
        # 是否分页
        self.has_page = False
        self.page_num = None
        self.size = None
        self.error = False

        self.serializer_instance = self.get_serializer_instance()

        self.default_empty_data = self.empty_response

        # 获取url参数
        self.url_data = self.get_url_data()
        self.url_data = self.url_data if self.url_data else {}

        # 获取body的参数
        self.body_data = self.get_body_data()
        self.body_data = self.body_data if self.body_data else {}

        # 组合参数
        self.data = self.get_data()
        if not self.data:
            self.data = {}

        # 通过serializer的model_class来获取一个基础查询
        self.qs = DataQuery(self.serializer.model_class, data=self.data, pk_field=self.pk_field,
                            fields=self.serializer.fields, paginate_field=self.paginate_field, query_set=self.query_set)

    @request_wrapper
    def dispatch_request(self, *args, **kwargs):
        meth = getattr(self, request.method.lower(), None)

        # If the request method is HEAD and we don't have a handler for it
        # retry with GET.
        if meth is None and request.method == 'HEAD':
            meth = getattr(self, 'get', None)

        if request.method.lower() == "get":
            if self.pk_field in request.args:
                meth = getattr(self, 'retrieve', None)
        self.meth = meth
        assert meth is not None, 'Unimplemented method %r' % request.method
        return meth(*args, **kwargs)

    def dispatch_before_request(self):
        # 分发请求前的执行
        before_request_meth = getattr(self, "before_" + request.method, None)
        if before_request_meth == "get":
            if self.pk_field in request.args:
                before_request_meth = getattr(self, 'before_retrieve', None)

        # self.data = self.get_data()
        # if not self.data:
        #     self.data = {}

        if before_request_meth:
            self.data = self.before_request_meth(self.data)

    def before_get(self, data):
        return data

    def before_retrieve(self, data):
        return data

    def before_post(self, data):
        return data

    def before_put(self, data):
        return data

    def before_delete(self, data):
        return data

    def dispatch_after_request(self, result):
        meth = getattr(self, "after_" + request.method.lower(), None)

        # If the request method is HEAD and we don't have a handler for it
        # retry with GET.
        # if meth is None and request.method == 'HEAD':
        #     meth = getattr(self, 'after_get', None)

        if meth == "get":
            if self.pk_field in request.args:
                meth = getattr(self, 'after_retrieve', None)

        if not meth:
            return self.default_result_handler(result)

        return meth(result)

    def default_result_handler(self, result):
        # 如果是两个参数 code, data 两个参数的时候会使用默认的code对应的msg
        # 如果是三个参数 code, msg, data
        if len(result) == 3:
            return jsonify(code=result[0], msg=result[1], data=result[2])
        elif len(result) == 2:
            return jsonify(code=result[0], msg=error_map[result[0]], data=result[1])
        else:
            raise ArgumentException

    def get_serializer_instance(self):
        # 获取序列化器的实例
        assert self.serializer is not None, "serializer 不能为空"
        return self.serializer()

    @staticmethod
    def get_url_data():
        # 获取url参数
        request_data = request.args.to_dict()
        return request_data

    @staticmethod
    def get_body_data():
        # 获取body传入的参数
        request_data = {}
        if not request.headers.get("content-type"):
            return request_data
        if "application/json" in request.headers.get("content-type"):
            request_data = request.json
        else:
            request_data = request.data
        return request_data

    def get_data(self):
        temp_data = {}
        if self.add_g_data:
            for gdi, gd in g.__dict__.items():
                if isinstance(gd, int) or isinstance(gd, str):
                    temp_data.update(**{gdi: gd})
        if request.method.lower() in ["get", "option", "head"]:
            temp_data.update(**self.url_data)
        else:
            self.body_data.update(**self.url_data)
            temp_data.update(**self.body_data)

        return temp_data
