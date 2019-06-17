from flask import Flask

from flask_sqlalchemy import SQLAlchemy

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
import redis


class BaseConfig(object):
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = r'mysql+pymysql://root:mysql@127.0.0.1:3306/t1'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    engine = create_engine(SQLALCHEMY_DATABASE_URI)
    Base = declarative_base(engine)

    SECRET_KEY = 'qyEzGidVnaRZNInFA6lO7AoPgIJGr83Em+wXttn8rBEGnbRswiviq5moyKDXG21j'
    SESSION_TYPE = 'redis'
    # 设置存储session的redis的地址
    SESSION_REDIS = redis.StrictRedis(host='127.0.0.1', port=6379, db=1)
    SESSION_COOKIE_NAME = 'session'
    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6379

    # 设置信息加密
    # SESSION_USE_SIGNER = True
    PERMANENT_SESSION_LIFETIME = 86400 * 7

    PER_PAGE = 5

    DANGEROUS_METHOD = ["POST", "PUT", "PATCH", "DELETE"]

    QRCODE_URL = "127.0.0.1:5001"


app = Flask(__name__)
app.config.from_object(BaseConfig)

db = SQLAlchemy()
db.init_app(app)
app.db = db

from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))
    sex = db.Column(db.String(20), default="男")


from v2.wrapper import PostView, GetView
from v2.wrapper import Serializer


class UserSerializer(Serializer):
    model_class = User
    fields = ["name"]


class UserView(GetView):
    serializer = UserSerializer


app.add_url_rule("/", view_func=UserView.as_view("bw"))

if __name__ == '__main__':
    print(app.url_map)
    print(app.extensions)
    app.run(debug=True)
    # manager.run()
