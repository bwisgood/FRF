from flask import jsonify

from .handler import ApiView
from .response_code import RET
from .exceptions import ArgumentException


class GetView(ApiView):
    def get(self):
        # 过滤出来需要的值
        query_data = self.qs.run_query("get")

        if not query_data:
            return RET.NODATA, None

        # 遍历查询到的实例列表，将每个实例都交给Serializer序列化之后传回给View
        items = []
        for instance in query_data:
            temp = self.serializer_instance.serialize(instance)
            items.append(temp)
        # 组织好之后返回数据
        return RET.OK, items


class RetrieveView(ApiView):
    def retrieve(self):
        # todo filling the blank
        # 查询到数据实例
        instance = self.qs.run_query("retrieve")
        if not instance:
            return RET.NODATA, None
        data = self.serializer_instance.serialize(instance)
        return RET.OK, data


class PostView(ApiView):
    def post(self):
        # 1.接收参数
        # 2.把参数传给serializer去增加一条数据
        data = self.serializer_instance.create(self.data, self.qs)
        # 2.1 serializer 先做参数校验
        # 2.2 如果参数校验有问题则直接返回 参数传入错误的异常
        # 2.3 serializer增加一条数据
        # 2.4 将增加后的实例做序列化
        # 2.5 交给View
        # 3. View组织参数返回
        return RET.OK, data


class PutView(ApiView):
    def put(self):
        # 1.接收参数
        # 2.根据主键pk_field查询到instance
        try:
            instance = self.qs.query_instance_with_pk()
        except ArgumentException:
            return RET.PARAMERR, None

        if not instance:
            return RET.NODATA, None
        # 3.将instance和接收到的参数传递给serializer
        data = self.serializer_instance.modify(instance, self.data, self.qs)
        # 3.1 参数校验
        # 3.2 赋值
        # 3.3 提交修改并返回修改后的实例
        # 3.4 将返回后的实例序列化
        # 4.返回修改后的数据
        return RET.OK, data


class DeleteView(ApiView):
    def delete(self):
        # 传入需要删除的主键
        # 根据主键查找到对应的实例

        # 传递给serializer做一次序列化
        # 删除数据
        # 组织数据并返回
        try:
            instance = self.qs.query_instance_with_pk()
        except ArgumentException:
            return RET.PARAMERR, None

        if not instance:
            return RET.NODATA, None

        data = self.serializer_instance.delete(instance, self.qs)
        return RET.OK, data
