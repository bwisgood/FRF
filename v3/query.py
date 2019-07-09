from inspect import isfunction

from sqlalchemy.exc import SQLAlchemyError
from flask import current_app

from .exceptions import ArgumentException


class DataQuery(object):
    def __init__(self, model_cls, qs=None, **kwargs):
        # model class
        self.model_cls = model_cls
        assert self.model_cls is not None
        # 查询参数
        self.data = kwargs.pop("data", None)
        self.pk_field = kwargs.pop("pk_field", None)
        self.order_by_fields = kwargs.pop("order_by_fields", None)

        self.like_fields = kwargs.pop("like_fields", None)
        self.fields = kwargs.pop("fields", None)
        self.paginate_field = kwargs.pop("paginate_field")

        self.query_set = kwargs.pop("query_set", None)
        if not qs:
            if self.query_set:
                if isinstance(self.query_set, dict):
                    self.qs = self.model_cls.query.filter_by(**self.query_set)
                elif isfunction(self.query_set):
                    self.qs = self.model_cls.query.filter_by(**self.query_set())
            else:
                self.qs = self.model_cls.query
        else:
            self.qs = qs

        self.db = current_app.extensions.get("sqlalchemy")

    def _filter_query_set(self, filter_data):
        # 过滤查询集
        if filter_data:
            self.qs = self.qs.filter_by(**filter_data)

    def query_instance_with_pk(self):
        # 获取主键
        pk = self.data.pop(self.pk_field)
        if not pk:
            raise ArgumentException
        # 根据主键查询
        instance = self.qs.filter_by(**{self.pk_field: pk}).first()
        return instance

    def _with_entities(self):
        """
        根据serializer获取固定的字段然后序列化
        :return:
        """

        if self.fields != "__all__":
            assert isinstance(self.fields, list)

            entities = []
            for field in self.fields:
                temp_attr = getattr(self.model_cls, field, None)
                if temp_attr:
                    entities.append(temp_attr)

            self.qs = self.qs.with_entities(*entities)

    def _order_by_query_set(self):
        if self.order_by_fields is not None:
            assert isinstance(self.order_by_fields, list)
            order_data = []
            for ob_field in self.order_by_fields:
                if ob_field.startswith("-"):
                    field = ob_field[1:]
                    ob_field_attr = getattr(self.model_cls, field, None)
                    if ob_field_attr is None:
                        raise SQLAlchemyError(
                            "%s not in %s" % (field, self.model_cls.__tablename__))
                    order_data.append(ob_field_attr.desc())
                else:
                    ob_field_attr = getattr(self.model_cls.model_class, ob_field, None)
                    if ob_field_attr is None:
                        raise SQLAlchemyError(
                            "%s not in %s" % (ob_field, self.model_cls.model_class.__tablename__))
                    order_data.append(ob_field_attr)

            self.qs = self.qs.order_by(*order_data)

    def _like_query_set(self):
        if self.like_fields is not None:
            assert isinstance(self.like_fields, list), "like field 必须是个列表"
            for field in self.like_fields:

                attr = getattr(self.model_cls, field, None)
                if attr:
                    if self.data.get(field):
                        self.qs = self.qs.filter(attr.like("%" + self.data.get(field) + "%"))

    def list_paginate(self, page_num=1, size=10, error=False):
        self.qs = self.qs.paginate(int(page_num), int(size), error)

    def run_query(self, meth):
        # 执行查询
        if meth == "get":
            self._filter_query_set(self.data)

            # 模糊查询
            self._like_query_set()
            # 过滤字段
            self._with_entities()
            # 排序
            self._order_by_query_set()
            # 分页
            if self.data is not None:
                page_num = self.data.pop(self.paginate_field[0], None)
                size = self.data.pop(self.paginate_field[1], None)
                error = self.data.pop(self.paginate_field[2], False)
            else:
                page_num = None
                size = None
                error = False

            if page_num and size:
                return self.list_paginate(page_num, size, error).items
            return self.qs.all()
        elif meth == "retrieve" or "put" or "delete":
            return self.query_instance_with_pk()
        else:
            # todo post
            return "post"

    def save(self, instance):
        self.db.add(instance)
        self.commit()
        return instance

    def commit(self):
        try:
            self.db.session.commit()
        except Exception:
            self.db.session.rollback()
            raise SQLAlchemyError

    def delete(self, instance):
        self.db.session.delete(instance)
