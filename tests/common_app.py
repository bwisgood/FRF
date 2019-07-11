import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base

from v3.wrapper import FlaskRestFramework
from v3.views import GetView, PostView, PutView, RetrieveView, DeleteView
from v3.serializer import Serializer

db = SQLAlchemy()
pwd = os.environ.get("FRF_MYSQL_PASSWORD") or "mysql"


def config():
    global db
    app = Flask(__name__)

    class Config(object):
        # 数据库配置
        SQLALCHEMY_DATABASE_URI = r'mysql+pymysql://root:{}@127.0.0.1:3306/test'.format(pwd)
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        engine = create_engine(SQLALCHEMY_DATABASE_URI)
        Base = declarative_base(engine)
        TESTING = True

    app.config.from_object(Config)
    db.init_app(app)
    frf = FlaskRestFramework()
    frf.init_app(app)
    return app


def test_without_db():
    # db = SQLAlchemy()
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URL"] = r'mysql+pymysql://root:{}@127.0.0.1:3306/test'.format(pwd)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config['TESTING'] = True
    # db.init_app(app)
    frf = FlaskRestFramework()
    frf.init_app(app)
    return app


class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30))
    gender = db.Column(db.String(30))


class PersonSerializer(Serializer):
    model_class = Person
    logical_delete = None


class PersonView(GetView):
    serializer = PersonSerializer
    look_up = ("name",)


class PersonPostView(PostView):
    serializer = PersonSerializer


class PersonPutView(PutView):
    serializer = PersonSerializer


class PersonDeleteView(DeleteView):
    serializer = PersonSerializer


from v3.mixins import AllMethodMixin, ReadOnlyMixin


class PersonRetrieveView(AllMethodMixin):
    serializer = PersonSerializer


app = config()

# app.add_url_rule('/persons', view_func=PersonView.as_view("person_view"))
# app.add_url_rule('/persons', view_func=PersonPostView.as_view("person_view_post"))
# app.add_url_rule('/persons', view_func=PersonPutView.as_view("person_view_put"))
# app.add_url_rule('/persons', view_func=PersonDeleteView.as_view("person_view_delete"))
app.add_url_rule('/persons', view_func=PersonRetrieveView.as_view("person_view_re"))

if __name__ == '__main__':
    ap = app.test_client()
    ap.post()
    ap.get()
    app.run(debug=True)
