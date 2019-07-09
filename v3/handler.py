from functools import wraps

from flask import jsonify, request
from flask.views import MethodView

from .exceptions import ArgumentException

from .response_code import RET
from .query import DataQuery
from .response_code import error_map


def request_wrapper(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        # 这里处理传入参数
        self.dispatch_before_request()
        # 这里写查询和序列化将返回的结果交给下一个
        result = func(self, *args, **kwargs)
        # 这里包装返回的参数
        result = self.dispatch_after_request(result)
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
        print(self.data)
        if not self.data:
            print(123)
            self.data = {}

        print("data", self.data)
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
                print(meth)
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
        print(type(result))
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
        if request.method.lower() in ["get", "option", "head"]:
            return self.url_data
        else:
            self.body_data.update(**self.url_data)
            return self.body_data

    # def filter_request_url_data(self):
    #     # 过滤请求数据查询对应的值
    #     filter_data = dict(filter(lambda x: x[0] in self.look_up, self.url_data.items()))
    #     return filter_data

    # def filter_query_set(self, filter_data):
    #     # 过滤查询集
    #     if filter_data:
    #         self.qs = self.qs.filter_by(**filter_data)

    # def run_query(self):
    #     # 执行查询
    #     # 模糊查询
    #     self.like_query_set()
    #     # 过滤字段
    #     self.with_entities()
    #     # 排序
    #     self.order_by_query_set()
    #     # 分页
    #     if self.has_page:
    #         self.list_paginate(self.page_num, self.size, self.error)
    #         return self.qs.items
    #
    #     return self.qs.all()
    #
    # def query_instance_with_pk(self):
    #     # 获取主键
    #     pk = self.data.pop(self.pk_field)
    #     if not pk:
    #         raise ArgumentException
    #     # 根据主键查询
    #     instance = self.qs.filter_by(**{self.pk_field: pk}).first()
    #     return instance
    #
    # def with_entities(self):
    #     """
    #     根据serializer获取固定的字段然后序列化
    #     :return:
    #     """
    #     fields = self.serializer_instance.fields
    #
    #     if fields != "__all__":
    #         assert isinstance(fields, list)
    #
    #         entities = []
    #         for field in fields:
    #             temp_attr = getattr(self.serializer_instance.model_class, field, None)
    #             if temp_attr:
    #                 entities.append(temp_attr)
    #
    #         self.qs = self.qs.with_entities(*entities)
    #
    # def order_by_query_set(self):
    #     if self.order_by_field is not None:
    #         assert isinstance(self.order_by_fields, list)
    #         order_data = []
    #         for ob_field in self.order_by_fields:
    #             if ob_field.startswith("-"):
    #                 field = ob_field[1:]
    #                 ob_field_attr = getattr(self.serializer_instance.model_class, field, None)
    #                 if ob_field_attr is None:
    #                     raise SQLAlchemyError(
    #                         "%s not in %s" % (field, self.serializer_instance.model_class.__tablename__))
    #                 order_data.append(ob_field_attr.desc())
    #             else:
    #                 ob_field_attr = getattr(self.serializer_instance.model_class, ob_field, None)
    #                 if ob_field_attr is None:
    #                     raise SQLAlchemyError(
    #                         "%s not in %s" % (ob_field, self.serializer_instance.model_class.__tablename__))
    #                 order_data.append(ob_field_attr)
    #
    #         self.qs = self.qs.order_by(*order_data)
    #
    # def like_query_set(self):
    #     if self.like_fields is not None:
    #         assert isinstance(self.like_fields, list)
    #         for field in self.like_fields:
    #
    #             attr = getattr(self.serializer.serializer_obj, field, None)
    #             if attr:
    #                 if self.data.get(field):
    #                     self.qs = self.qs.filter(attr.like("%" + self.data.get(field) + "%"))
    #
    # def math_query_set(self):
    #     pass
    #
    # def list_paginate(self, page_num=1, size=10, error=False):
    #     self.qs = self.qs.paginate(int(page_num), int(size), error)
