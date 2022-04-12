#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=too-few-public-methods
''' hyperbitch '''

import uuid

from flask_security import RoleMixin, UserMixin
from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Text)
from sqlalchemy.orm import backref, relationship
from sqlalchemy.sql import func

from hyperbitch.database import Base
from hyperbitch.helpers import GUID


# Flask security = user registration and auth management
class RolesUsers(Base):
    ''' Which roles belong to an user '''

    __tablename__ = 'roles_users'

    id = Column(Integer(), primary_key=True)
    user_id = Column('user_id', Integer(), ForeignKey('user.id'))
    role_id = Column('role_id', Integer(), ForeignKey('role.id'))

class Role(Base, RoleMixin):
    ''' Roles '''

    __tablename__ = 'role'

    id = Column(Integer(), primary_key=True)
    name = Column(String(80), unique=True)
    description = Column(String(255))

class User(Base, UserMixin):
    ''' Users '''

    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True)
    username = Column(String(255), unique=True, nullable=True)
    password = Column(String(255), nullable=False)
    last_login_at = Column(DateTime())
    current_login_at = Column(DateTime())
    last_login_ip = Column(String(100))
    current_login_ip = Column(String(100))
    login_count = Column(Integer)
    active = Column(Boolean())
    fs_uniquifier = Column(String(255), unique=True, nullable=False)
    confirmed_at = Column(DateTime())
    roles = relationship('Role', secondary='roles_users',
                         backref=backref('users', lazy='dynamic'))
    #whichsjobs = relationship('SingleJob', backref=backref('users', lazy='dynamic'))
    #whichrobs = relationship('RepeatingJob', backref=backref('users', lazy='dynamic'))
    whichsjobs = relationship('SingleJob', backref('users'), lazy=True)
    whichrobs = relationship('RepeatingJob', backref('users'), lazy=True)

# Native app DB Schema
class BitchBase(Base):
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
    user_id = Column('user_id', Integer(), ForeignKey('user.id'))

class RepeatingJob(BitchBase):
    ''' table of continuous jobs'''

    __tablename__ = 'repeatingjob'

    whento = Column(String, nullable=False)
    whichsingles = relationship('SingleJob', backref='repeatingjob', lazy=True)
    user_id = Column('user_id', Integer(), ForeignKey('user.id'))
