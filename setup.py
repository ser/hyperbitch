#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='hyperbitch',
    packages=['hyperbitch'],
    include_package_data=True,
    install_requires=[
        'flask',
        'bootstrap-flask',
        'jinja_markdown',
    ],
)
