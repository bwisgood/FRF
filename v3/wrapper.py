from .handler import ApiView
from .docs import DocDataCollector
from .exceptions import FRFErrorHandler


class FlaskRestFramework(object):
    """
    初始化程序时使用的类，用来写内部需要的一些app的runtime variable
    """

    used_cls = []

    def __init__(self, app=None, **kwargs):
        self.accept_errors = kwargs.pop("accept_errors", None)
        self.global_request_auth_cls = kwargs.pop("global_request_auth", None)

        # self.error_handler = FRFErrorHandler(self.accept_errors)
        self.error_handler = kwargs.pop("error_handler", None)
        self.app = app
        self.db = None
        self.ApiView = None

        if app is not None:
            self.init_app(app, **kwargs)

        self.doc_data_collector = DocDataCollector()
        # self.get_app_url_map()
        # self.generate_html_interface_docs()

    def init_app(self, app, **kwargs):
        self.app = app
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['frf'] = self

        self.db = app.extensions.get("sqlalchemy")
        if not self.db:
            raise ImportError("未找到sqlalchemy,请确认是否已安装sqlalchemy"
                              "并将本extension的初始化置于sqlalchemy初始化之后")
        # 注册frf错误处理
        if self.error_handler:
            self.error_handler.register_handler(app)
        else:
            self.error_handler = FRFErrorHandler(self.accept_errors)
            self.error_handler.register_handler(app)

        # 注册全局请求权限处理
        if self.global_request_auth_cls:
            app.before_request(self.global_request_auth_cls.auth)

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
        from v3.docs import BaseDocData
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
