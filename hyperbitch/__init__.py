#!/usr/bin/env python
# -*- coding: utf-8 -*-
''' hyperbitch '''

import uuid

import redis
import toml
from flask import Flask, g, redirect, render_template, request, url_for
from flask_babel import Babel
from flask_bootstrap import Bootstrap5
from flask_kvsession import KVSessionExtension
from flask_login import current_user
from flask_security import Security, SQLAlchemyUserDatastore, auth_required
from flask_security.models import fsqla_v2 as fsqla
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from simplekv.memory.redisstore import RedisStore
from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.orm import backref, declarative_base, relationship
from sqlalchemy.sql import func
from sqlalchemy_repr import PrettyRepresentableBase
from werkzeug.middleware.proxy_fix import ProxyFix
from wtforms import (BooleanField, DateTimeField, StringField, SubmitField,
                     TextAreaField)
from wtforms.validators import DataRequired

from hyperbitch.helpers import GUID

app = Flask(__name__)
app.config.from_file("../../hyperbitch-config.toml", load=toml.load)

Base = declarative_base(cls=PrettyRepresentableBase)

# pylint: disable=wrong-import-position disable=too-few-public-methods disable=no-member
import hyperbitch.views.public

#import hyperbitch.views.user

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
    #__tablename__ = 'users'
    ''' Define default user DB '''
    #whichsingles = relationship('SingleJob', backref='singlejob', lazy=True)
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

# Native app DB Schema
class BitchBase(db.Model, Base):
    ''' Base model '''

    __abstract__ = True

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    descr = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime,
                           default=func.current_timestamp(),
                           onupdate=func.current_timestamp())
    finished_at = Column(DateTime)

class SingleJob(BitchBase):
    ''' table of single jobs '''

    __tablename__ = 'singlejob'

    isrepeat = Column(GUID(), ForeignKey('repeatingjob.id'), nullable=True)
    user_id = Column(Integer, ForeignKey(User.id))

class RepeatingJob(BitchBase):
    ''' table of continuous jobs'''

    __tablename__ = 'repeatingjob'

    cronschedule = Column(String, nullable=False)
    whento = Column(String, nullable=False)
    whichsingles = relationship('SingleJob', backref='repeatingjob', lazy=True)
    user_id = Column(Integer, ForeignKey(User.id))

# Create DB if does not exist
@app.before_first_request
def create_db():
    ''' Create DB if does not exist '''
    db.create_all()

#if current_user.is_authenticated():
#    g.user = current_user.get_id()

# Forms
class AddTask(FlaskForm):
    ''' Add a task Form '''
    name = StringField('name', validators=[DataRequired()])
    descr = TextAreaField('descr')
    isrepeat = BooleanField('isrepeat')
    cronschedule = StringField('cronschedule')
    whento = DateTimeField('whento')
    submit = SubmitField()

# Flask translations
@babel.localeselector
def get_locale():
    ''' activating translations '''
    return request.accept_languages.best_match(app.config['LANGUAGES'])

#from jinja_markdown import MarkdownExtension
#jinja_env.add_extension(MarkdownExtension)

@app.route('/dashboard')
@auth_required()
def dashboard():
    ''' dashboard page'''

    #job = SingleJob(name='job2', user_id=1 )
    #db.session.add(job)
    #db.session.commit()
    return render_template('dashboard.html')

@app.route('/task', methods=['GET', 'POST'])
@app.route('/task/<uuid:id>', methods=['GET', 'POST'])
@auth_required()
def task(id):
    ''' adding a task '''

    form = AddTask()

    if form.validate_on_submit():
        return redirect(url_for('dashboard'))

    return render_template('task.html', form=form)

@app.route('/admin/all_users')
@auth_required()
def all_users():
    ''' all users table '''
    data = User.query.all()
    return render_template('raw_table.html', data=data)

@app.route('/admin/all_singlejobs')
@auth_required()
def all_singlejobs():
    ''' all singlejobs table '''
    data = SingleJob.query.all()
    return render_template('raw_table.html', data=data)

@app.route('/admin/all_repeatingjobs')
@auth_required()
def all_repeatingjobs():
    ''' all repeatingjobs table '''
    data = RepeatingJob.query.all()
    return render_template('raw_table.html', data=data)

if __name__ == '__main__':
    app.jinja_env.auto_reload = True
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
    app.run()
