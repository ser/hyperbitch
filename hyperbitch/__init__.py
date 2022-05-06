#!/usr/bin/env python
# -*- coding: utf-8 -*-
''' hyperbitch '''

import datetime
import uuid

import redis
import toml
from flask import Flask, flash, g, redirect, render_template, request, url_for
from flask_babel import Babel
from flask_bootstrap import Bootstrap5
from flask_kvsession import KVSessionExtension
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import current_user
from flask_security import Security, SQLAlchemyUserDatastore, auth_required
from flask_security.models import fsqla_v2 as fsqla
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from simplekv.memory.redisstore import RedisStore
from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql import func
from sqlalchemy_repr import PrettyRepresentableBase
from werkzeug.middleware.proxy_fix import ProxyFix
from wtforms import (BooleanField, DateField, IntegerField, StringField,
                     SubmitField, TextAreaField)
from wtforms.validators import DataRequired

from hyperbitch.helpers import GUID

app = Flask(__name__)
app.config.from_file("../../hyperbitch-config.toml", load=toml.load)


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
limiter = Limiter(app, key_func=get_remote_address)
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

#@app.before_request
#def load_user():
#    if current_user.is_authenticated:
#        g.user = current_user.get_id()
#    print(current_user.is_authenticated)

# Flask translations
@babel.localeselector
def get_locale():
    ''' activating translations '''
    return request.accept_languages.best_match(app.config['LANGUAGES'])


#####################################
# DATABASE SCHEMA
#####################################
class BitchBase(db.Model):
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

    planned_for = Column(DateTime)
    isrepeat = Column(GUID(), ForeignKey('repeatingjob.id'), nullable=True)
    user_id = Column(Integer, ForeignKey(User.id))


class RepeatingJob(BitchBase):
    ''' table of continuous jobs'''

    __tablename__ = 'repeatingjob'

    weekschedule = Column(String, nullable=False)
    monthschedule = Column(String, nullable=False)
    whento = Column(DateTime, nullable=False)
    whichsingles = relationship('SingleJob', backref='repeatingjob', lazy=True)
    user_id = Column(Integer, ForeignKey(User.id))


#####################################
# FORMS
#####################################
class AddSTask(FlaskForm):
    ''' Add a task Form '''
    name = StringField('name', validators=[DataRequired()])
    descr = TextAreaField('descr', render_kw={"rows": 14, "cols": 50})
    planned_for = DateField('planned_for', validators=[DataRequired()])
    submit = SubmitField()


class AddRTask(FlaskForm):
    ''' Repeating task Form '''
    name = StringField('name', validators=[DataRequired()])
    descr = TextAreaField('descr', render_kw={"rows": 14, "cols": 50})
    weekschedule = StringField('weekschedule')
    monthschedule = StringField('monthschedule')
    whento = DateField('whento')
    submit = SubmitField()


#####################################
# FUNCTIONS
#####################################
def close_and_create_next():
    ''' Close one instance of repeating task and create another. '''

def todate(datestring):
    ''' convert string to date for router. '''
    return datetime.datetime.strptime(datestring, "%Y-%m-%d").date()


#####################################
# ROUTES
#####################################

@app.route('/dashboard')
@auth_required()
def dashboard():
    ''' dashboard page'''

    #job = SingleJob(name='job2', user_id=1 )
    #db.session.add(job)
    #db.session.commit()
    return render_template('dashboard.html')


@app.route('/day', methods=['GET', 'POST'])
@app.route('/day/<string:day>', methods=['GET', 'POST'])
@auth_required()
def dayschedule(day=None):
    ''' Showing one day of work plans, day format:
        "%Y-%m-%d"
    '''
    if day:
        daytasks = SingleJob.query.filter(
            func.date(SingleJob.planned_for)==todate(day)).all()
    else:
        today = datetime.date.today()
        daytasks = SingleJob.query.filter(
            func.date(SingleJob.planned_for)==today).all()

    return render_template('dayschedule.html', daytasks=daytasks)


@app.route('/done/<uuid:tid>')
@app.route('/done/<uuid:tid>/<int:tdone>')
@limiter.limit("1/second")
@auth_required()
def mark_done(tid, tdone=None):
    ''' Marking task as done.'''
    record = SingleJob.query.filter_by(id=tid).first_or_404()
    # check if task belongs to user!
    if current_user.has_role("admin") or current_user.id == record.user_id:
        if tdone == 0:
            record.finished_at = None
        else:
            record.finished_at = datetime.datetime.utcnow()
        db.session.commit()
        flash('Task marked as done!', 'info')
    else:
        flash('Something went wrong', 'danger')
    return redirect(url_for('dayschedule'))


@app.route('/task', methods=['GET', 'POST'])
@app.route('/task/<uuid:tid>', methods=['GET', 'POST'])
@limiter.limit("1/second")
@auth_required()
def stask(tid=None):
    ''' adding or modyfing a single task '''

    if tid:
        record = SingleJob.query.get(tid)
    else:
        record = SingleJob()
    form = AddSTask(obj=record)

    if form.validate_on_submit():
        form.populate_obj(record)
        # if task does not have a user assigned, we assign current user
        if not record.user_id:
            record.user_id=current_user.id
        # TO-DO: in future form could allow modifying task user by admin
        db.session.add(record)
        db.session.commit()
        flash('Task added!', 'info')
        return redirect(url_for('dashboard'))

    return render_template('stask.html', form=form)


@app.route('/repeat', methods=['GET', 'POST'])
@app.route('/repeat/<uuid:tid>', methods=['GET', 'POST'])
@limiter.limit("1/second")
@auth_required()
def rtask(tid=None):
    ''' adding or modyfing a repeating task '''

    if tid:
        record = RepeatingJob.query.get(tid)
    else:
        record = RepeatingJob()
    form = AddRTask(obj=record)

    if form.validate_on_submit():
        form.populate_obj(record)
        # if task does not have a user assigned, we assign current user
        if not record.user_id:
            record.user_id=current_user.id
        # TO-DO: in future form could allow modifying task user by admin
        db.session.add(record)
        db.session.commit()
        flash('Task added!', 'info')
        return redirect(url_for('dashboard'))

    return render_template('rtask.html', form=form)


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

############################################
# MAIN
############################################
if __name__ == '__main__':
    app.jinja_env.auto_reload = True
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1)
    app.run()
