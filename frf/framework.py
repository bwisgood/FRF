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
        if self.look_up is None:
            return self.get_query_set()
        else:
            request_data = self.get_request_data()
            query_look_up = {}
            for _look_up in self.look_up:
                if not request_data:
                    continue
                rd = request_data.get(_look_up)
                if rd:
                    query_look_up[_look_up] = rd
            return self.get_query_set().filter_by(**query_look_up)

    def filter_queryset(self):
        query_set = self._filter_queryset()
        query_set = self._order_by_query_set(query_set)
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
        assert meth is not None, 'Unimplemented method %r' % request.method
        return meth(*args, **kwargs)

    def perform_save(self, request_data, temp_instance=None):
        """
        执行创建
        :param serializer:
        :param request_data:
        :return:
        """
        serializer = self.get_serializer_class()

        #

        # filter_data = request_data.get(self.pk_field)
        # temp_instance = self.get_instance(filter_data={self.pk_field: filter_data})
        # print(id(temp_instance))
        #
        try:
            if temp_instance is None:
                instance = serializer.save(request_data)
            else:
                instance = serializer.save(request_data, temp_instance)

        except AttributeError:
            return None
        except TypeError:
            return None
        except SQLAlchemyError as e:
            print(e.__str__())
            return None
        return serializer, instance
        # return serializer, temp_instance

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

    def list_paginate(self, query_set, page_num=1, size=10, error=False):
        query_set = query_set.paginate(int(page_num), int(size), error)
        return query_set
