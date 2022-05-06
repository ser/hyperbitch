#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" setup the app """

from setuptools import setup

setup(
    name='hyperbitch',
    packages=['hyperbitch'],
    include_package_data=True,
    install_requires=[
        'argon2-cffi',
        'bootstrap-flask',
        'flask',
        'flask-babel',
        'flask-kvsession-fork',
        'flask-limiter',
        'flask-markdown',
        'flask-security-too[fsqla,common]',
        'redis',
        'sqlalchemy-repr',
    ],
)
