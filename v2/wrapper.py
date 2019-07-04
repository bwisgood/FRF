from functools import wraps
from flask import request, jsonify, current_app
from flask.views import MethodView
from v2.response_code import RET
from v2.exceptions import *
from sqlalchemy.exc import SQLAlchemyError
from inspect import isfunction
from v2.docs import DocDataCollector


def request_wrapper(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        self.dispatch_before_request()
        result = func(self, *args, **kwargs)
        self.dispatch_after_request(result)
        return result

    return wrapper


class FlaskRestFramework(object):
    """
    初始化程序时使用的类，用来写内部需要的一些app的runtime variable
    """

    used_cls = []

    def __init__(self, app=None, **kwargs):
        self.app = app
        self.db = None
        self.ApiView = None

        if app is not None:
            self.init_app(app, **kwargs)

        self.doc_data_collector = DocDataCollector()
        self.generate_html_interface_docs()

    def init_app(self, app, **kwargs):
        self.app = app
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['frf'] = self

        self.db = app.extensions.get("sqlalchemy")
        if not self.db:
            raise ImportError("未找到sqlalchemy,请确认是否已安装sqlalchemy"
                              "并将本extension的初始化置于sqlalchemy初始化之后")

    # todo usual logger
    # html api
    def generate_html_interface_docs(self):
        from flask import render_template_string
        if self.app.config["DEBUG"] is True:
            @self.app.route("/docs")
            def generate_docs():
                with open("show_api.html") as f:
                    s = f.read()
                return render_template_string(s, all_data=self.doc_data_collector.data)

    def collect_sub_class_use_frf(self):
        """收集所有使用frf的View"""
        """
        需要的东西：
            1.接口的路由
            2.接口支持的method
            3.每种方法的传入参数
            4.每种方法的返回参数
            
        
        1.收集所有使用frf的view
        2.去urlmap中寻找对应的view 如果没找到则排除掉
        
        """
        """
        方案1：
            使用一个装饰器来捕获所有用到的view ✔️
        方案2：
            去app.view_function中遍历出来所有继承ApiView的function
        """
        base = {}
        from inspect import isclass
        for endpoint, func in self.app.view_functions.items():
            if not isclass(func):
                continue
            if issubclass(func, ApiView):
                base[endpoint] = func

    def get_app_url_map(self):
        rl = []
        sl = []
        from v2.docs import BaseDocData
        for i in list(self.app.url_map.iter_rules()):
            bs = {}
            bs["endpoint"] = i.endpoint
            view_func = self.app.view_functions.get(i.endpoint)
            bs["view_func"] = view_func
            bs["rule"] = i.rule
            bs["methods"] = i.methods
            try:
                if issubclass(view_func, ApiView):
                    base_data = BaseDocData(**bs)
                    self.doc_data_collector.add(base_data)
                    rl.append(bs)
                else:
                    sl.append(bs)
            except TypeError as e:
                print(e)
                sl.append(bs)

        print(rl)
        print(sl)


class BaseView(type):
    def __new__(mcs, name, base, attrs):
        return type.__new__(mcs, name, base, attrs)


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

    @staticmethod
    def empty_response():
        return jsonify(code=RET.NODATA, msg='没有数据', data=None)

    def __init__(self):
        # 继承父类的初始化方法
        super().__init__()
        # 是否分页
        self.has_page = False
        self.page_num = None
        self.size = None
        self.error = False

        self.serializer_instance = self.get_serializer_instance()

        self.default_empty_data = self.empty_response

        # 获取url参数
        self.url_data = self.get_url_data()  # example.com?a=1&b=2
        self.url_data = self.url_data if self.url_data else {}

        # 获取body的参数
        self.body_data = self.get_body_data()
        self.body_data = self.body_data if self.body_data else {}

        # 组合参数
        self.data = self.get_data()
        self.data = self.data if self.data else {}

        # 通过serializer的model_class来获取一个基础查询
        if self.query_set:
            if isinstance(self.query_set, dict):
                self.qs = self.serializer_instance.model_class.query.filter_by(**self.query_set)
            elif isfunction(self.query_set):
                self.qs = self.serializer_instance.model_class.query.filter_by(**self.query_set())
        else:
            self.qs = self.serializer_instance.model_class.query

        self.db = current_app.extensions.get("sqlalchemy")

    @request_wrapper
    def dispatch_request(self, *args, **kwargs):
        # 分发请求
        meth = getattr(self, request.method.lower(), None)

        # If the request method is HEAD and we don't have a handler for it
        # retry with GET.
        if meth is None and request.method == 'HEAD':
            meth = getattr(self, 'get', None)

        assert meth is not None, 'Unimplemented method %r' % request.method
        return meth(*args, **kwargs)

    def dispatch_before_request(self):
        # 分发请求前的执行
        before_request_meth = getattr(self, "before_" + request.method, None)
        if before_request_meth:
            before_request_meth()

    def dispatch_after_request(self, result):
        # 分发请求后的执行
        after_request_meth = getattr(self, "after_" + request.method, None)
        if after_request_meth:
            after_request_meth(result)

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
            return self.get_url_data()
        else:
            return self.get_body_data().update(**self.get_url_data())

    def filter_request_url_data(self):
        # 过滤请求数据查询对应的值
        filter_data = dict(filter(lambda x: x[0] in self.look_up, self.url_data.items()))
        return filter_data

    def filter_query_set(self, filter_data):
        # 过滤查询集
        if filter_data:
            self.qs = self.qs.filter_by(**filter_data)

    def run_query(self):
        # 执行查询
        # 模糊查询
        self.like_query_set()
        # 过滤字段
        self.with_entities()
        # 排序
        self.order_by_query_set()
        # 分页
        if self.has_page:
            self.list_paginate(self.page_num, self.size, self.error)
            return self.qs.items

        return self.qs.all()

    def query_instance_with_pk(self):
        # 获取主键
        pk = self.data.pop(self.pk_field)
        if not pk:
            raise ArgumentException
        # 根据主键查询
        instance = self.qs.filter_by(**{self.pk_field: pk}).first()
        return instance

    def with_entities(self):
        """
        根据serializer获取固定的字段然后序列化
        :return:
        """
        fields = self.serializer_instance.fields

        if fields != "__all__":
            assert isinstance(fields, list)

            entities = []
            for field in fields:
                temp_attr = getattr(self.serializer_instance.model_class, field, None)
                if temp_attr:
                    entities.append(temp_attr)

            self.qs = self.qs.with_entities(*entities)

    def order_by_query_set(self):
        if self.order_by_field is not None:
            assert isinstance(self.order_by_fields, list)
            order_data = []
            for ob_field in self.order_by_fields:
                if ob_field.startswith("-"):
                    field = ob_field[1:]
                    ob_field_attr = getattr(self.serializer_instance.model_class, field, None)
                    if ob_field_attr is None:
                        raise SQLAlchemyError(
                            "%s not in %s" % (field, self.serializer_instance.model_class.__tablename__))
                    order_data.append(ob_field_attr.desc())
                else:
                    ob_field_attr = getattr(self.serializer_instance.model_class, ob_field, None)
                    if ob_field_attr is None:
                        raise SQLAlchemyError(
                            "%s not in %s" % (ob_field, self.serializer_instance.model_class.__tablename__))
                    order_data.append(ob_field_attr)

            self.qs = self.qs.order_by(*order_data)

    def like_query_set(self):
        if self.like_fields is not None:
            assert isinstance(self.like_fields, list)
            for field in self.like_fields:

                attr = getattr(self.serializer.serializer_obj, field, None)
                if attr:
                    if self.data.get(field):
                        self.qs = self.qs.filter(attr.like("%" + self.data.get(field) + "%"))

    def math_query_set(self):
        pass

    def list_paginate(self, page_num=1, size=10, error=False):
        self.qs = self.qs.paginate(int(page_num), int(size), error)


class GetView(ApiView):
    def get(self):
        # 过滤出来需要的值
        filter_data = self.filter_request_url_data()

        if filter_data is not None:
            self.page_num = filter_data.pop(self.paginate_field[0], None)
            self.size = filter_data.pop(self.paginate_field[1], None)
            self.error = filter_data.pop(self.paginate_field[2], False)

        if self.page_num and self.size:
            self.has_page = True

        self.filter_query_set(filter_data)
        query_data = self.run_query()

        # 如果查询到空数据则返回空数据的json
        if not query_data:
            return self.default_empty_data()

        # 遍历查询到的实例列表，将每个实例都交给Serializer序列化之后传回给View
        items = []
        for instance in query_data:
            temp = self.serializer_instance.serialize(instance)
            items.append(temp)
        # 组织好之后返回数据
        return jsonify(code=RET.OK, msg='查询成功', data=items)


class PostView(ApiView):
    def post(self):
        # 1.接收参数
        # 2.把参数传给serializer去增加一条数据
        data = self.serializer_instance.create(self.data)
        # 2.1 serializer 先做参数校验
        # 2.2 如果参数校验有问题则直接返回 参数传入错误的异常
        # 2.3 serializer增加一条数据
        # 2.4 将增加后的实例做序列化
        # 2.5 交给View
        # 3. View组织参数返回
        return jsonify(code=RET.OK, msg='添加成功', data=data)


class PutView(ApiView):
    def put(self):
        # 1.接收参数
        data = self.data
        # 2.根据主键pk_field查询到instance
        try:
            instance = self.query_instance_with_pk()
        except ArgumentException:
            return jsonify(code=RET.PARAMERR, msg='没有传入主键', data=None)

        if not instance:
            return jsonify(code=RET.NODATA, msg='没有找到对应主键的数据', data=None)
        # 3.将instance和接收到的参数传递给serializer
        data = self.serializer_instance.modify(instance, data)
        # 3.1 参数校验
        # 3.2 赋值
        # 3.3 提交修改并返回修改后的实例
        # 3.4 将返回后的实例序列化
        # 4.返回修改后的数据
        return jsonify(code=RET.OK, msg='修改成功', data=data)


class DeleteView(ApiView):
    def delete(self):
        # 传入需要删除的主键
        # 根据主键查找到对应的实例

        # 传递给serializer做一次序列化
        # 删除数据
        # 组织数据并返回
        try:
            instance = self.query_instance_with_pk()
        except ArgumentException:
            return jsonify(code=RET.PARAMERR, msg='没有传入主键', data=None)

        if not instance:
            return jsonify(code=RET.NODATA, msg='没有找到对应主键的数据', data=None)

        data = self.serializer_instance.delete(instance)
        return jsonify(code=RET.OK, msg='删除成功', data=data)


class ExceptionHandler(object):
    """处理运行中的异常"""
    pass


if __name__ == '__main__':
    from flask import Flask

    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = r'mysql+pymysql://root:mysql@127.0.0.1:3306/ai_community_v3'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
    app.config['SQLALCHEMY_ECHO'] = True
    app.config['DEBUG'] = True

    from flask_sqlalchemy import SQLAlchemy

    db = SQLAlchemy(app)
    frf = FlaskRestFramework(app)

    from v2.serializer import Serializer


    class AModel(db.Model):
        __tablename__ = "amodel"
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(30))
        address = db.Column(db.String(30))


    class ASerialzier(Serializer):
        model_class = AModel


    class A(GetView, PostView):
        serializer = ASerialzier
        look_up = ("name", "address")


    app.add_url_rule("/a", view_func=A)

    frf.get_app_url_map()
    # frf.collect_sub_class_use_frf()
    app.run(debug=True)
