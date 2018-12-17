from functools import wraps

from flask.views import MethodView
from flask import jsonify, request
from sqlalchemy.exc import SQLAlchemyError
from apps import db


def request_wrapper(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self.dispatch_before_request()
        result = func(self, *args, **kwargs)
        # self.dispatch_after_request(result)
        self.dispatch_after_request(result)
        return result

    return wrapper


class APIView(MethodView):
    """
    query_set： 查询集
    serializer_class： 序列化类
    look_up：查询字段
    pk_field：单条详细字段
    """
    session = db.session
    # query_set = {"isdelete":0}
    query_set = None
    serializer_class = None
    # look_up = {"id":1, "name": "123"}///("id","name")
    look_up = None
    paginate_field = ("page_num", "size", "error")
    pk_field = "id"
    no_body_method = ("get", "head", "option")
    # order_by_field = ("id","-age")
    order_by_field = None
    like_field = None
    auth_manager = None
    special_look_up = None

    def __init__(self):
        super(APIView, self).__init__()
        self.request_data = self.get_request_data()
        self.serializer = self.get_serializer_class()

    def get_request_data(self):
        """
        获取请求的数据
        可重写
        :return:
        """
        if request.method.lower() not in self.no_body_method:
            # request_data = request.json
            request_data = None
            headers = {header_key: header_value for header_key, header_value in request.headers.items(True)}
            if "content-type" not in headers:
                headers["content-type"] = "contenttype"
            if "application/json" in headers.get("content-type").lower():
                request_data = request.json
                # if request.form.to_dict() is not None:
                #     request_data = request.form.to_dict()
        else:
            request_data = request.args.to_dict() if request.args else None

        if request_data is None:
            request_data = {}

        global_func = getattr(self, "change_request_data", None)
        if global_func:
            request_data = global_func(request_data)

        request_meth = request.method.lower()
        func = getattr(self, request_meth + "_change_request_data", None)

        if func:
            request_data = func(request_data)

        print(request_data)
        return request_data

    def get_query_set(self):
        """
        获取查询集
        :return:
        """
        serializer = self.get_serializer_class()
        if self.query_set is not None:
            assert isinstance(self.query_set, dict)
            query_set = serializer.model_class.query.filter_by(**self.query_set)
        # assert self.query_set is not None, (
        #     "'%s' should either include a `query_set` attribute, "
        #     "or override the `get_queryset()` method."
        #     % self.__class__.__name__
        # )
        else:
            query_set = serializer.model_class.query
        # query_set = self.query_set
        global_func = getattr(self, "after_get_query_set", None)
        if global_func:
            query_set = global_func(query_set)

        meth_name = request.method.lower() + "_after_get_query_set"

        meth = getattr(self, meth_name, None)
        if meth is not None:
            query_set = meth(query_set)
        return query_set

    def _order_by_query_set(self, query_set):
        serializer = self.get_serializer_class()
        if self.order_by_field is None:
            return query_set
        order_data = []
        for ob_field in self.order_by_field:
            if ob_field.startswith("-"):
                field = ob_field[1:]
                ob_field_attr = getattr(serializer.model_class, field, None)
                if ob_field_attr is None:
                    raise SQLAlchemyError("%s not in %s" % (field, serializer.model_class.__tablename__))
                order_data.append(ob_field_attr.desc())
            else:
                ob_field_attr = getattr(serializer.model_class, ob_field, None)
                if ob_field_attr is None:
                    raise SQLAlchemyError("%s not in %s" % (ob_field, serializer.model_class.__tablename__))
                order_data.append(ob_field_attr)

        return query_set.order_by(*order_data)

    def _filter_queryset(self):
        """
        获取过滤后的查询集
        :return:
        """
        qs = self.get_query_set()
        if request.method.lower() == "get":
            if self.look_up is None:
                return qs
            else:
                query_look_up = {}
                for _look_up in self.look_up:
                    if not self.request_data:
                        break
                    rd = self.request_data.get(_look_up)
                    if rd:
                        query_look_up[_look_up] = rd
                return qs.filter_by(**query_look_up)
        else:
            return qs

    def _special_filter_queryset(self, qs):
        """
        特殊过滤 gt lt in not_in
        :return:
        """
        if self.special_look_up is None:
            return qs
        for i in self.special_look_up:
            qs = self._method_mix(qs, i)
        return qs

    def _method_mix(self, qs, lk):
        # 小于，大于，不等于，in列表
        meth_list = ["<", ">", "!", "["]
        method = lk[0:1]
        if method not in meth_list:
            return qs

        field = lk[1:]
        model_class = self.serializer.model_class
        attr = getattr(model_class, field, None)
        if not attr:
            raise SQLAlchemyError("%s has no field %s" % ("table", field))

        if method == "<":
            qs = qs.filter(attr < self.request_data.get(field))
        elif method == ">":
            qs = qs.filter(attr > self.request_data.get(field))
        elif method == "!":
            qs = qs.filter(attr != self.request_data.get(field))
        elif method == "[":
            qs = qs.filter(attr.in_(self.request_data.get(field)))

        return qs

    def _like_query_set(self, query_set):
        if self.like_field:
            for field in self.like_field:

                attr = getattr(self.serializer.serializer_obj, field, None)
                if attr:
                    if self.request_data.get(field):
                        query_set = query_set.filter(attr.like("%" + self.request_data.get(field) + "%"))
        return query_set

    def filter_queryset(self):
        query_set = self._filter_queryset()
        if request.method.lower() == "get":
            query_set = self._like_query_set(query_set)
            query_set = self._order_by_query_set(query_set)
            query_set = self._special_filter_queryset(query_set)
        return query_set

    def get_instance(self, filter_data):
        instance_trial = self.filter_queryset().filter_by(**filter_data).all()
        if len(instance_trial) > 1:
            raise SQLAlchemyError("查询集只能返回一个结果 请核对lookup参数")
        elif len(instance_trial) < 1:
            raise SQLAlchemyError("没有查询到数据")
        instance = instance_trial[0]
        print(id(instance))
        return instance

    def get_serializer_class(self):
        """
        获取序列化类对象
        :return:
        """
        serializer_instance = self.serializer_class()

        return serializer_instance

    def dispatch_before_request(self):
        """
        分发处理函数之前的函数，以before_开始
        :return:
        """
        meth = getattr(self, "before_" + request.method.lower(), None)

        # If the request method is HEAD and we don't have a handler for it
        # retry with GET.
        # if meth is None and request.method == 'HEAD':
        #     meth = getattr(self, 'before_get', None)

        if meth == "get":
            if self.pk_field in request.args:
                meth = getattr(self, 'after_retrieve', None)

        if meth is None:
            return None

        return meth()

    def dispatch_after_request(self, result):
        """
        分发处理函数之后的函数，以after_开始
        :param result:
        :return:
        """
        meth = getattr(self, "after_" + request.method.lower(), None)

        # If the request method is HEAD and we don't have a handler for it
        # retry with GET.
        # if meth is None and request.method == 'HEAD':
        #     meth = getattr(self, 'after_get', None)

        if meth == "get":
            if self.pk_field in request.args:
                meth = getattr(self, 'after_retrieve', None)

        if meth is None:
            return None

        return meth(result)

    @request_wrapper
    def dispatch_request(self, *args, **kwargs):
        """
        重写分发的响应
        :param args:
        :param kwargs:
        :return:
        """
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

    def perform_save(self, request_data, temp_instance=None):
        """
        执行创建
        :param temp_instance:
        :param request_data:
        :return:
        """

        #

        # filter_data = request_data.get(self.pk_field)
        # temp_instance = self.get_instance(filter_data={self.pk_field: filter_data})
        # print(id(temp_instance))

        try:
            if temp_instance is None:
                instance = self.serializer.save(request_data)
            else:
                instance = self.serializer.save(request_data, temp_instance)

        except AttributeError:
            return None
        except TypeError:
            return None
        except SQLAlchemyError as e:
            print(e.__str__())
            return None
        return self.serializer, instance
        # return serializer, temp_instance

    def bulk_save(self, request_data):
        """
        批量添加
        :param request_data:
        :return:
        """
        try:
            db.session.bulk_insert_mappings(self.serializer.model_class, request_data)
        except Exception as e:
            db.session.rollback()
            return False
        return True

    def perform_delete(self, instance):
        print(instance)
        # instance.delete()

        # serializer = self.get_serializer_class()
        # serializer.destroy(instance)
        if hasattr(instance, "is_delete"):
            instance.is_delete = 1
        else:
            db.session.delete(instance)
        db.session.commit()
        return None

    def bulk_delete(self, pk_list):
        """
        批量删除
        :param id_list:
        :return:
        """
        pk_attr = getattr(self.serializer.model_class, self.pk_field, None)
        try:
            self.serializer.model_class.filter(pk_attr.in_(pk_list)).delete(synchronize_session=False)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return False
        return True

    def list_paginate(self, query_set, page_num=1, size=10, error=False):
        query_set = query_set.paginate(int(page_num), int(size), error)
        return query_set
