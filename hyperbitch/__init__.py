#!/usr/bin/env python
# -*- coding: utf-8 -*-
''' hyperbitch '''

import datetime
import uuid
from logging.config import dictConfig

import pendulum
import redis
import toml
from dateutil.relativedelta import relativedelta
from flask import (Flask, flash, jsonify, redirect, render_template, request,
                   url_for)
from flask_babel import Babel
from flask_bootstrap import Bootstrap5
from flask_kvsession import KVSessionExtension
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import current_user
from flask_mail import Mail
from flask_security import (Security, SQLAlchemyUserDatastore, auth_required,
                            roles_accepted)
from flask_security.models import fsqla_v2 as fsqla
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flaskext.markdown import Markdown
from simplekv.memory.redisstore import RedisStore
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from werkzeug.middleware.proxy_fix import ProxyFix
from wtforms import (BooleanField, DateField, IntegerField, StringField,
                     SubmitField, TextAreaField)
from wtforms.validators import DataRequired

from hyperbitch.helpers import GUID

# logging
dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(levelname)s in %(module)s: %(message)s',
        }
    },
    'handlers': {
        'journal': {
            'class': 'logging.handlers.SysLogHandler',
            'address':  '/dev/log',
            'formatter': 'default',
            'level': 'DEBUG'
        }
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['journal']
    }
})

#####################
# INIT
#####################

app = Flask(__name__)
app.config.from_file("../../hyperbitch-config.toml", load=toml.load)


# MAIL config
# pylint: disable=wrong-import-position disable=too-few-public-methods disable=no-member
import hyperbitch.views.public

#import hyperbitch.views.user

# KVSession keeps its data in redis, as it's temporary
# and we don't want to backup it during db backup
store = RedisStore(
        redis.StrictRedis(
            host=app.config['REDIS_HOST'],
            port=app.config['REDIS_PORT'],
            password=app.config['REDIS_PASSWORD']
        ))

# Flask extensions
babel = Babel(app)
bootstrap = Bootstrap5(app)
db = SQLAlchemy(app)
limiter = Limiter(app, key_func=get_remote_address)
mail = Mail(app)
md = Markdown(app)
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
    finished_at = Column(DateTime)
    updated_at = Column(DateTime,
                           default=func.current_timestamp(),
                           onupdate=func.current_timestamp())


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
    whichsingles = relationship('SingleJob', backref='repeatingjob', lazy=True)
    user_id = Column(Integer, ForeignKey(User.id))


#####################################
# FORMS
#####################################
class AddSTask(FlaskForm):
    ''' Add a task Form '''
    name = StringField(
            'Short name of the task',
            validators=[DataRequired()])
    descr = TextAreaField(
            'Description, you can use markdown syntax',
            render_kw={"rows": 14, "cols": 50})
    planned_for = DateField(
            'Which day the task is planned for',
            validators=[DataRequired()])
    submit = SubmitField()


class AddRTask(FlaskForm):
    ''' Repeating task Form '''
    name = StringField(
            'Short name of the task',
            validators=[DataRequired()])
    descr = TextAreaField(
            'Description, you can use markdown syntax',
            render_kw={"rows": 14, "cols": 50})
    weekschedule = StringField(
            'Weekly schedule, week days as numbers separated with comma, for example - every Monday and Thursday: 1,4')
    monthschedule = StringField(
            'Monthly schedule, days of the month separarated with comma, for example - every 5th and 18th day of the month: 5,18')
    finished_at = DateField(
            'When the task should stop repeating')
    submit = SubmitField()


#####################################
# FUNCTIONS
#####################################
def todate(datestring):
    ''' convert string to date for router. '''
    return datetime.datetime.strptime(datestring, "%Y-%m-%d").date()

def closest_day_week(weekschedule):
    ''' find closest day in weekly schedule '''
    today = pendulum.today()
    wlist = list(map(int, weekschedule.split(',')))
    tmp_y = []
    for tmp_x in wlist:
        nextd = None
        if tmp_x == 1:
            nextd = today.next(pendulum.MONDAY)
        elif tmp_x == 2:
            nextd = today.next(pendulum.TUESDAY)
        elif tmp_x == 3:
            nextd = today.next(pendulum.WEDNESDAY)
        elif tmp_x == 4:
            nextd = today.next(pendulum.THURSDAY)
        elif tmp_x == 5:
            nextd = today.next(pendulum.FRIDAY)
        elif tmp_x == 6:
            nextd = today.next(pendulum.SATURDAY)
        elif tmp_x == 7:
            nextd = today.next(pendulum.SUNDAY)
        if nextd:
            tmp_y.append(nextd)
    # find closest one from all
    return min(tmp_y, key=lambda d: abs(d - today))

def closest_day_month(monthschedule):
    ''' find closest day in monthly schedule '''
    today = pendulum.today()
    dinm = today.days_in_month
    mlist = list(map(int, monthschedule.split(',')))
    tmp_y = []
    for tmp_x in mlist:
        nextd = None
        if tmp_x <= dinm: # verify if we have such many days this month
            if tmp_x < today.day:
                nextd = today.start_of('month') + relativedelta(months=1) \
                    + relativedelta(days=tmp_x-1)
            elif tmp_x > today.day:
                nextd = today.start_of('month') + relativedelta(days=tmp_x-1)
            elif tmp_x == today.day:
                nextd = today
        # TO-DO! here must be algorithm dealing with days 31 etc.
        if nextd:
            tmp_y.append(nextd)
    return min(tmp_y, key=lambda d: abs(d - today))

def createsinglefromrepeating(tid):
    ''' This function creates a new single
    task based on nearest timing required for repeating task'''
    record = RepeatingJob.query.get(tid)
    today = pendulum.today()

    # sanity check if the task has not expired
    if pendulum.instance(record.finished_at) < today:
        return "Not creating. Repeating task has already expired!"
    # sanity check if there is already an unfinished child task
    singlejobs = SingleJob.query.filter_by(isrepeat=tid).filter_by(finished_at=None).all()
    if singlejobs:
        return "Not creating. Another childrens task is already added and active."

    # seeking for another closest day of the week
    closestw = None
    if record.weekschedule:
        closestw = closest_day_week(record.weekschedule)
        app.logger.debug(f'closestw: {closestw}')

    # seeking for another closest day in the month
    closestm = None
    if record.monthschedule:
        closestm = closest_day_month(record.monthschedule)
        app.logger.debug(f'closestm: {closestm}')

    if closestw and closestm:
        nextschedule = min([closestw, closestm], key=lambda d: abs(d - today))
    elif closestw:
        nextschedule = closestw
    elif closestm:
        nextschedule = closestm
    app.logger.info(f'Creating task for {nextschedule}.')

    singlejob = SingleJob(
        planned_for=nextschedule,
        name=record.name,
        descr=record.descr,
        isrepeat=record.id,
        user_id=record.user_id
        )
    db.session.add(singlejob)
    db.session.commit()

    return "OK"

#####################################
# ROUTES
#####################################

@app.route('/dashboard')
@auth_required()
def dashboard():
    ''' dashboard page'''
    return render_template('dashboard.html')


@app.route('/day', methods=['GET', 'POST'])
@app.route('/day/<string:day>', methods=['GET', 'POST'])
@auth_required()
def dayschedule(day=None):
    ''' Showing one day of work plans, day format:
        "%Y-%m-%d"
    '''
    if day:
        today = todate(day)
    else:
        today = pendulum.today()

    # first we seek for outdated unfinished tasks
    query = SingleJob.query.filter(
            func.date(SingleJob.planned_for)<today).filter(
                    SingleJob.finished_at==None)
    if current_user.has_role("admin"):
        exptasks = query.all()
    else:
        exptasks = query.filter_by(
                user_id=current_user.id).all()

    # second we gather all tasks for particular day
    query = SingleJob.query.filter(
            func.date(SingleJob.planned_for)==today)
    if current_user.has_role("admin"):
        daytasks = query.all()
    else:
        daytasks = query.filter_by(
                user_id=current_user.id).all()

    # we combine these two
    alltasks = exptasks + daytasks

    return render_template(
        'taskgroup.html',
        tasks=alltasks,
        title_header="Day schedule"
    )


@app.route('/done/<uuid:tid>/<int:tdone>')
@limiter.limit("1/second")
@auth_required()
def mark_done(tid, tdone=None):
    ''' Marking single task as done / not done.
        Creating another instance of task if repeating.
    '''
    record = SingleJob.query.filter_by(id=tid).first_or_404()
    app.logger.debug(record)

    # check if task belongs to user or admin!
    if current_user.has_role("admin") or current_user.id == record.user_id:
        app.logger.info(f'Marking task {tid} as {tdone}.')
        if tdone == 0:
            record.finished_at = None
            flash('Task marked as NOT done!', 'warning')
        else:
            record.finished_at = datetime.datetime.utcnow()
            flash('Task marked as done!', 'info')
            # if it is a child of repeating task, create another single task
            if record.isrepeat:
                app.logger.info('As the task is repeating we create another instance.')
                app.logger.info(createsinglefromrepeating(record.isrepeat))
        db.session.commit()
    else:
        flash('Something went wrong', 'danger')
        return redirect(url_for('dashboard'))

    return redirect(url_for('dayschedule'))


@app.route('/task', methods=['GET', 'POST'])
@app.route('/task/<uuid:tid>', methods=['GET', 'POST'])
@limiter.limit("1/second")
@auth_required()
def stask(tid=None):
    ''' adding or modyfing a single task '''
    if tid:
        record = SingleJob.query.get(tid)
        # verify if task belongs to the current user
        if not current_user.has_role("admin") and record.user_id != current_user.id:
            return redirect(url_for('dashboard'))
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
        flash('Task added or modified!', 'info')
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
        # verify if task belongs to the current user
        if not current_user.has_role("admin") and record.user_id != current_user.id:
            return redirect(url_for('dashboard'))
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

        # we need to create a first single task which is a child of repeating task
        createsinglefromrepeating(record.id)

        # signal to the user that all went fine
        flash('Task added or modified!', 'info')
        return redirect(url_for('dashboard'))

    return render_template('rtask.html', form=form)


@app.route('/all_repeating/<string:switch>')
@auth_required()
def all_repeating(switch):
    ''' Show all repeating tasks. '''
    if switch == "active":
        query = RepeatingJob.query.filter(
            RepeatingJob.finished_at>=pendulum.today())
        if current_user.has_role("admin"):
            repeatingjobs = query.all()
        else:
            repeatingjobs = query.filter_by(
                    user_id=current_user.id).all()
    elif switch == "past":
        query = RepeatingJob.query.filter(
            RepeatingJob.finished_at<pendulum.today())
        if current_user.has_role("admin"):
            repeatingjobs = query.all()
        else:
            repeatingjobs = query.filter_by(
                user_id=current_user.id).all()
    else:
        return redirect(url_for('dashboard'))

    return render_template(
        'taskgroup.html',
        tasks=repeatingjobs,
        title_header="All repeating tasks"
    )


@app.route('/events/all')
@auth_required()
def events_all():
    ''' Single tasks to show inside dashboard calendar '''
    query = SingleJob.query.filter_by(
            finished_at=None)
    if current_user.has_role("admin"):
        singlejobs = query.all()
    else:
        singlejobs = query.filter_by(
                user_id=current_user.id).all()
    allevents = []
    for job in singlejobs:
        jobdate = pendulum.instance(job.planned_for)
        event = {
            "id": job.id,
            "allDay": True,
            "title": job.name,
            "start": jobdate.to_iso8601_string(),
            "end": jobdate.to_iso8601_string(),
            "url": "/day/" + jobdate.to_date_string()
        }
        allevents.append(event)
    return jsonify(allevents)


@app.route('/events/sidebar')
@auth_required()
def events_sidebar():
    ''' shortcuts for sidebar calendar '''
    today = pendulum.today()
    allevents = []
    for day in range(1, today.days_in_month+1):
        jobdate = pendulum.datetime(today.year, today.month, day)
        query = SingleJob.query.filter_by(
            finished_at=None).filter_by(
            planned_for=jobdate)
        if current_user.has_role("admin"):
            singlejobs = query.all()
        else:
            singlejobs = query.filter_by(
                    user_id=current_user.id).all()
        event = {
            "id": day,
            "allDay": True,
            "title": len(singlejobs),
            "start": jobdate.to_iso8601_string(),
            "end": jobdate.to_iso8601_string(),
            "url": "/day/" + jobdate.to_date_string()
        }
        allevents.append(event)
    return jsonify(allevents)


@app.route('/admin/all_users')
@auth_required()
@roles_accepted('admin')
def all_users():
    ''' all users table '''
    data = User.query.all()
    return render_template('raw_table.html', data=data)


@app.route('/admin/all_singlejobs')
@auth_required()
@roles_accepted('admin')
def all_singlejobs():
    ''' all singlejobs table '''
    data = SingleJob.query.all()
    return render_template('raw_table.html', data=data)


@app.route('/admin/all_repeatingjobs')
@auth_required()
@roles_accepted('admin')
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
