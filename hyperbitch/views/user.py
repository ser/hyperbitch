# -*- coding: utf-8 -*-
""" users views """

from flask import render_template

from hyperbitch import app

#from jinja_markdown import MarkdownExtension
#jinja_env.add_extension(MarkdownExtension)

@app.route('/dashboard')
def dashboard():
    ''' dashboard page'''
    return render_template('dashboard.html')
