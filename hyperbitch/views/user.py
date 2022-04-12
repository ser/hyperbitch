# -*- coding: utf-8 -*-
""" users views """

from flask import render_template
from flask_security import auth_required

from hyperbitch import app

#from jinja_markdown import MarkdownExtension
#jinja_env.add_extension(MarkdownExtension)

@app.route('/dashboard')
@auth_required()
def dashboard():
    ''' dashboard page'''


    from hyperbitch import SingleJob


    job1 = SingleJob(name='job1', user_id=1 )
    app.db.session.add(job1)
    app.db.session.commit()
    return render_template('dashboard.html')
