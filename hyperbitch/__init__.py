#!/usr/bin/env python
# -*- coding: utf-8 -*-
''' hyperbitch '''

import redis
import toml
from flask import Flask, request
from flask_babel import Babel
from flask_bootstrap import Bootstrap5
from flask_kvsession import KVSessionExtension
from flask_security import (Security, SQLAlchemySessionUserDatastore,
                            auth_required, current_user, hash_password)
from simplekv.memory.redisstore import RedisStore
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from werkzeug.middleware.proxy_fix import ProxyFix

from hyperbitch.database import db_session, init_db
from hyperbitch.helpers import GUID
from hyperbitch.models import Role, User

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
kvs = KVSessionExtension(store, app)

# Setup Flask-Security
user_datastore = SQLAlchemySessionUserDatastore(db_session, User, Role)
security = Security(app, user_datastore)

# Create DB if does not exist
@app.before_first_request
def create_db():
    ''' Create DB if does not exist '''
    init_db()

# Flask translations
@babel.localeselector
def get_locale():
    ''' activating translations '''
    return request.accept_languages.best_match(app.config['LANGUAGES'])

if __name__ == '__main__':
    app.jinja_env.auto_reload = True
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
    app.run()
