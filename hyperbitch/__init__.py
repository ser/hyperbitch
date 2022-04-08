#!/usr/bin/env python
# -*- coding: utf-8 -*-
''' hyperbitch '''

import toml
from flask import Flask
from flask_bootstrap import Bootstrap5

app = Flask(__name__)
app.config.from_file("../../hyperbitch-config.toml", load=toml.load)

# pylint: disable=wrong-import-position
import hyperbitch.views.public
import hyperbitch.views.user

bootstrap = Bootstrap5(app)

if __name__ == '__main__':
    app.jinja_env.auto_reload = True
    app.run()
