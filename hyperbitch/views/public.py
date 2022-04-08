# -*- coding: utf-8 -*-
""" public views """

from flask import render_template

from hyperbitch import app


@app.route('/')
def home():
    ''' main page'''
    return render_template('home.html')
