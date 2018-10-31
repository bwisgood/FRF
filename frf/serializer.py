from inspect import ismethod

from apps import db


class Serializer(object):
    serializer_obj = None
    fields = "__all__"

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
        assert self.serializer_obj is not None, "serializer_obj can not be None"
        self.relations = []
        self.model_class = self.get_serializer_obj()
        self.table = self.model_class.__dict__.get('__table__')
        self.foreign_keys = self.get_all_foreign_keys()
        self.extra_func = [ismethod(getattr(self.model_class, attr[0], None)) for attr in
                           self.model_class.__dict__.items()]
        self.all_fields = self.get_all_fields()

    def get_all_fields(self):
        """
        获取所有字段
        :return:
        """
        all_attr_str_list = list(self.table.c)
        all_fields = [str(c).split(".")[1] for c in all_attr_str_list]
        # all_fields = []
        # for attr in all_attr:
        #     # 暂定使用foreign_keys属性区分是否是字段
        #     _attr = getattr(self.model_class, attr, None)
        #     if _attr is not None:
        #         try:
        #             foreign_keys_attr = attr.foreign_keys
        #             all_fields.append(foreign_keys_attr)
        #             if len(foreign_keys_attr):
        #                 self.foreign_keys.append(_attr)
        #         except Exception as e:
        #             if not ismethod(_attr):
        #                 self.relations.append(_attr)
        #             else:
        #                 self.extra_func.append(_attr)
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

    def get_serializer_obj(self):
        """
        获取要序列化的类
        :return:
        """
        serializer_obj = self.serializer_obj
        return serializer_obj

    def validate(self, data=None, params_validate=False):
        """
        参数校验
        :param data: 参数
        :param params_validate: 是否做字段参数校验
        :return:
        """
        if data is not None:
            assert isinstance(data, dict), 'param "data" must be dict'
            for column in self.all_fields:
                c_obj = getattr(self, "validate_" + column, None)
                if c_obj:
                    data[column] = c_obj(data.get(column))
        if params_validate:
            for field in self.all_fields:
                # 非空校验
                _column = getattr(self.model_class, field, None)
                assert _column is not None, "%s not in %s" % (field, self.model_class.__tablename__)
                if _column.nullable is False and data.get(field) is None and not _column.primary_key:
                    raise AttributeError("%s参数未传入" % field)
            # 类型校验
            # 如果类型在_map中则做校验
            for _data_key, _data_value in data.items():
                column = getattr(self.model_class, _data_key, None)
                assert column is not None, "%s not in %s" % (_data_key, self.model_class.__tablename__)
                column_type = column.type.__visit_name__
                if column_type in self._map:
                    incident_type = self._map.get(column_type)
                    try:
                        if _data_value is not None:
                            data[_data_key] = incident_type(_data_value)
                    except Exception as e:
                        raise TypeError("[%s]必须是[%s]类型" % (_data_key, column_type))
        return data

    def serialize_return_data(self, data):
        """
        序列化返回值
        :param data: 参数
        :return: 参数data
        """
        if self.fields == '__all__':
            return_data = dict(filter(lambda x: x[0] in self.all_fields, data.items()))
        else:
            return_data = dict(filter(lambda x: x[0] in self.all_fields and x[0] in self.fields, data.items()))
        return return_data

    def save(self, data, instance=None):
        # 校验需要保存的参数
        if instance is not None:

            validate_data = {i: getattr(instance, i, None) for i in self.all_fields}
            validate_data.update(**data)
            self.validate(validate_data, params_validate=True)
            for _data_key, _data_value in data.items():
                # instance_attr = getattr(instance, _data_key, None)
                setattr(instance, _data_key, _data_value)
            db.session.commit()

        else:
            instance = self.model_class()

            for _data_key, _data_value in data.items():
                # instance_attr = getattr(instance, _data_key, None)
                setattr(instance, _data_key, _data_value)
            db.session.add(instance)
            db.session.commit()
        return instance

    def destroy(self, instance):
        instance.delete()
        db.session.delete(instance)
        db.session.commit()
        return None

    def __str__(self):
        return "|".join(self.all_fields)
