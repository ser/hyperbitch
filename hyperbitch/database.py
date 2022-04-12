#!/usr/bin/env python
# -*- coding: utf-8 -*-
''' hyperbitch '''

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from sqlalchemy_repr import PrettyRepresentableBase

#from hyperbitch import app
#engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
engine = create_engine("sqlite:///../../hyperbitch.db")

db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))

Base = declarative_base(cls=PrettyRepresentableBase)
Base.query = db_session.query_property()

def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    import hyperbitch.models
    Base.metadata.create_all(bind=engine)
