import threading
from v2.utils import translate


class DocDataCollector(object):
    _instance_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not hasattr(DocDataCollector, "_instance"):
            with DocDataCollector._instance_lock:
                if not hasattr(DocDataCollector, "_instance"):
                    DocDataCollector._instance = object.__new__(cls)
        return DocDataCollector._instance

    def __init__(self):
        self.data = []

    def add(self, doc_data):
        if isinstance(doc_data, BaseDocData):
            self.data.append(doc_data)

    def __str__(self):
        if not self.data:
            return "NO DATA YET"

        return "\n".join(self.data)


class BaseDocData(object):
    def __init__(self, *args, **kwargs):
        self.endpoint = kwargs.pop("endpoint")
        self.rule = kwargs.pop("rule")
        self.methods = kwargs.pop("methods")
        self.view_func = kwargs.pop("view_func")

        # self.extract_input_params()
        # self.extract_output_params()
        self.doc_data_list = []

        output_params = self.extract_output_params()
        print(output_params)
        for method in self.methods:
            input_params = self.extract_input_params(method)
            doc_data = DocData(method=method, rule=self.rule, input_params=input_params,
                               output_params=output_params)
            self.doc_data_list.append(doc_data)

        # self.input_params = []
        # self.search_input_params = []
        # self.output_params = []

    def extract_input_params(self, method):
        s = self.view_func.serializer
        p = []
        if method == "GET":
            if self.view_func.look_up:
                for i in self.view_func.look_up:
                    # _column = getattr(self.view_func.serializer.model_class, i, None)
                    # if not _column:
                    #     continue
                    p.append(Param(name=i, type_="string", fill=True, comment=translate(i)))
                    # self.input_params.append(p)
        elif method == "POST":
            all_fields = s.get_all_fields()
            for field in all_fields:
                _column = getattr(self.view_func.serializer.model_class, field, None)
                if not _column:
                    continue
                p.append(Param(name=field, type_=_column.type.__visit_name__, fill=_column.nullable,
                               comment=translate(field)))
                # self.input_params.append(p)
            pass
        elif method == "PUT":
            all_fields = s.model_class.get_all_fields()
            for field in all_fields:
                _column = getattr(self.view_func.serializer.model_class, field, None)
                if not _column:
                    continue
                p.append(Param(name=field, type_=_column.type.__visit_name__, fill=_column.nullable,
                               comment=translate(field)))
                # self.input_params.append(p)
        elif method == "DELETE":
            p.append(Param(name="id", type_="int", fill=True, comment="主键id"))
            # self.input_params.append(p)

        return p

    def extract_output_params(self):
        s = self.view_func.serializer
        if s.fields == "__all__":
            f = s.get_all_fields()
        else:
            f = getattr(s, "fields", None)
        fs = []
        for field in f:
            _column = getattr(self.view_func.serializer.model_class, field, None)
            fs.append(Param(name=field, type_=_column.type.__visit_name__, comment=translate(field)))

        return fs

    def __str__(self):
        return "[endpoint:{} rule:{} methods:{} view_func:{}]".format(self.endpoint, self.rule, self.methods,
                                                                      self.view_func.__name__)


class DocData(object):
    def __init__(self, method, rule, input_params, output_params):
        self.method = method
        self.rule = rule
        self.input_params = input_params
        self.output_params = output_params


class Param(object):
    def __init__(self, **kwargs):
        self.name = kwargs.pop("name")
        self.type_ = kwargs.pop("type_")
        self.fill = kwargs.pop("fill", None)
        self.comment = kwargs.pop("comment")


class Combinator(object):
    def __init__(self, collector):
        self.collector = collector
