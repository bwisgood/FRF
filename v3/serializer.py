from inspect import ismethod
from datetime import datetime

from .exceptions import ArgumentException


class Serializer(object):
    model_class = None
    fields = "__all__"
    extend_fields = None
    logical_delete = {"is_delete": 0}
    data_time_format = "%Y/%m/%d %H:%M:%S"
    _map = {
        "integer": int,
        "small_integer": int,
        "boolean": bool,
        "string": str,
        # "datetime": datetime,
        # "date": date,
        "float": float
        # "time"
    }

    def __init__(self):
        """
        self.relations： 所有relations
        self.model_class： 序列化的类对象
        self.table: sqlalchemy的table对象
        self.foreign_keys： 所有外键
        self.extra_func：额外的方法
        self.all_fields：所有字段
        """
        assert self.model_class is not None, "serializer_obj can not be None"
        self.relations = []
        self.table = self.model_class.__dict__.get('__table__')
        self.foreign_keys = self.get_all_foreign_keys()
        self.extra_func = [ismethod(getattr(self.model_class, attr[0], None)) for attr in
                           self.model_class.__dict__.items()]
        self.all_fields = self.get_all_fields()

    @classmethod
    def get_all_fields(cls):
        """
        获取所有字段
        :return:
        """
        all_attr_str_list = list(cls.model_class.__dict__.get("__table__").c)
        all_fields = [str(c).split(".")[1] for c in all_attr_str_list]
        return all_fields

    def get_all_foreign_keys(self):
        """
        获取所有字段
        :return:
        """
        tmp = []
        fks = self.table.foreign_keys
        for fk in fks:
            tmp.append(fk.parent.name)
        return tmp

    def add_extend_fields(self, return_data):
        if self.extend_fields is None:
            return return_data
        for item in self.extend_fields.items():
            # 查询值
            data = return_data.get(item[0])
            if data is not None:
                return_data.pop(item[0])
            else:
                continue
            extra_data = item[1].query.filter_by(**{"id": data}).first()

            extend_fields_in = getattr(self, "extend_fields_" + item[0], None)
            if extend_fields_in:

                return_data1 = dict(
                    map(self.mapping_func,
                        dict(filter(lambda x: x[0] in extend_fields_in, extra_data.__dict__.items())).items()))
            else:
                return_data1 = dict(
                    map(self.mapping_func,
                        dict(filter(lambda x: not x[0].startswith("_"), extra_data.__dict__.items())).items()))
            return_data.update(**{item[0]: return_data1})
        return return_data

    def mapping_func(self, y):
        if isinstance(y[1], datetime):
            temp = y[1].strftime(self.data_time_format)
            return y[0], temp
        else:
            return y

    def serialize(self, instance):
        """
        序列化返回值
        :param instance: 实例
        :return: 参数data
        """

        data = self.to_serializer_able(instance)

        if self.fields == '__all__':

            return_data = dict(map(self.mapping_func, data.items()))
        else:
            assert isinstance(self.fields, list)
            return_data = dict(
                map(self.mapping_func, dict(filter(lambda x: x[0] in self.fields, data.items())).items()))
        return_data = self.add_extend_fields(return_data)
        return return_data

    def to_serializer_able(self, instance):
        data_ = {}
        for field in self.all_fields:
            data_[field] = getattr(instance, field, None)
        return data_

    def create(self, data, qs):
        # 先做排除无用数据
        data = self.filter_table_data(data)
        # 再拿去做校验和类型转换
        data = self.validate(data)

        # 创建实例
        instance = self.model_class()
        # 将data的值传递给实例赋值
        # print(data)
        for k, v in data.items():
            setattr(instance, k, v)
        # 保存instance

        instance = qs.save(instance)

        # 返回序列化之后的数据
        return self.serialize(instance)

    def validate(self, data):
        # 校验参数
        for field in self.all_fields:
            # 先非空校验
            _column = getattr(self.model_class, field, None)
            match_data = data.get(_column)
            self.check_field_not_none(_column, match_data)
            # 再做类型校验
            self.check_field_type(_column, match_data, data)
        return data

    @staticmethod
    def check_field_not_none(_column, match_data):
        if _column.nullable is False and match_data is None and not _column.primary_key:
            raise ArgumentException

    def check_field_type(self, _column, match_data, data):
        if match_data is not None:
            column_type = _column.type.__visit_name__
            if column_type in self._map:
                incident_type = self._map.get(column_type)
                try:
                    # 用转换过的类型做一次匹配
                    data[_column] = incident_type(match_data)
                except Exception:
                    raise ArgumentException

    def filter_table_data(self, data):
        # 过滤一遍data，将不属于table的属性排除
        assert isinstance(data, dict)
        data = dict(filter(lambda x: x[0] in self.all_fields, data.items()))
        return data

    def modify(self, instance, data, qs):
        # 先过滤一遍data，将不属于table的属性排除
        data = self.filter_table_data(data)
        # 在做一次参数校验
        data = self.validate(data)
        for k, v in data.items():
            setattr(instance, k, v)
        qs.commit()
        return self.serialize(instance)

    def delete(self, instance, qs):
        # 判断是否需要逻辑删除
        data = self.serialize(instance)
        if not self.logical_delete:
            qs.delete(instance)
        else:
            for k, v in self.logical_delete:
                setattr(instance, k, v)
        qs.commit()
        return data
