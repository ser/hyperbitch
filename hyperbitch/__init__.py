#!/usr/bin/env python
# -*- coding: utf-8 -*-
''' hyperbitch '''

import redis
import toml
from flask import Flask, request
from flask_babel import Babel
from flask_bootstrap import Bootstrap5
from flask_kvsession import KVSessionExtension
from flask_security import Security, SQLAlchemyUserDatastore
from flask_security.models import fsqla_v2 as fsqla
from flask_sqlalchemy import SQLAlchemy
from simplekv.memory.redisstore import RedisStore
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.config.from_file("../../hyperbitch-config.toml", load=toml.load)

# pylint: disable=wrong-import-position
import hyperbitch.views.public
import hyperbitch.views.user

# KVSession keeps its data in redis, as it's temporary
# and we don't want to backup it during db backup
store = RedisStore(redis.StrictRedis())

# Flask extensions
babel = Babel(app)
bootstrap = Bootstrap5(app)
db = SQLAlchemy(app)
kvs = KVSessionExtension(store, app)

# Flask security = user registration and auth management
fsqla.FsModels.set_db_info(db)
class Role(db.Model, fsqla.FsRoleMixin):
    ''' Define default user roles DB '''
class User(db.Model, fsqla.FsUserMixin):
    ''' Define default user DB '''
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

# Create DB if does not exist
@app.before_first_request
def create_db():
    ''' Create DB if does not exist '''
    db.create_all()

# Flask translations
@babel.localeselector
def get_locale():
    ''' activating translations '''
    return request.accept_languages.best_match(app.config['LANGUAGES'])

if __name__ == '__main__':
    app.jinja_env.auto_reload = True
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
    app.run()
