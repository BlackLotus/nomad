# Copyright 2018 Markus Scheidgen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an"AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This module comprises the nomad@FAIRDI APIs. Currently there is NOMAD's official api, and
we will soon at the optimade api. The app module also servers documentation, gui, and
alive.
"""
from flask import Flask, Blueprint, jsonify, url_for, abort, request
from flask_restplus import Api
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from werkzeug.wsgi import DispatcherMiddleware  # pylint: disable=E0611
import os.path
import random
from structlog import BoundLogger

from nomad import config, utils as nomad_utils

from .api import blueprint as api
from .optimade import blueprint as optimade
from .docs import blueprint as docs

logger: BoundLogger = None
""" A logger pre configured with information about the current request. """

base_path = config.services.api_base_path
""" Provides the root path of the nomad APIs. """


@property  # type: ignore
def specs_url(self):
    """
    Fixes issue where swagger-ui makes a call to swagger.json over HTTP.
    This can ONLY be used on servers that actually use HTTPS.  On servers that use HTTP,
    this code should not be used at all.
    """
    return url_for(self.endpoint('specs'), _external=True, _scheme='https')


if config.services.https:
    Api.specs_url = specs_url


app = Flask(__name__)
""" The Flask app that serves all APIs. """

app.config.APPLICATION_ROOT = base_path  # type: ignore
app.config.RESTPLUS_MASK_HEADER = False  # type: ignore
app.config.RESTPLUS_MASK_SWAGGER = False  # type: ignore
app.config.SWAGGER_UI_OPERATION_ID = True  # type: ignore
app.config.SWAGGER_UI_REQUEST_DURATION = True  # type: ignore

app.config['SECRET_KEY'] = config.services.api_secret


def api_base_path_response(env, resp):
    resp('200 OK', [('Content-Type', 'text/plain')])
    return [
        ('Development nomad api server. Api is served under %s/.' %
            config.services.api_base_path).encode('utf-8')]


app.wsgi_app = DispatcherMiddleware(  # type: ignore
    api_base_path_response, {config.services.api_base_path: app.wsgi_app})


CORS(app)

app.register_blueprint(api, url_prefix='/api')
app.register_blueprint(optimade, url_prefix='/optimade')
app.register_blueprint(docs, url_prefix='/docs')


@app.errorhandler(Exception)
def handle(error: Exception):
    status_code = getattr(error, 'code', 500)
    if not isinstance(status_code, int):
        status_code = 500
    name = getattr(error, 'name', 'Internal Server Error')
    description = getattr(error, 'description', 'No description available')
    data = dict(
        code=status_code,
        name=name,
        description=description)
    data.update(getattr(error, 'data', []))
    response = jsonify(data)
    response.status_code = status_code
    if status_code == 500:
        local_logger = logger
        # the logger is created in before_request, if the error was created before that
        # logger can be None
        if local_logger is None:
            local_logger = nomad_utils.get_logger(__name__)

        local_logger.error('internal server error', exc_info=error)

    return response


@app.route('/alive')
def alive():
    """ Simple endpoint to utilize kubernetes liveness/readiness probing. """
    return "I am, alive!"


@app.before_request
def before_request():
    # api logger
    global logger
    logger = nomad_utils.get_logger(
        __name__,
        blueprint=str(request.blueprint),
        endpoint=request.endpoint,
        method=request.method,
        json=request.json,
        args=request.args)

    # chaos monkey
    if config.services.api_chaos > 0:
        if random.randint(0, 100) <= config.services.api_chaos:
            abort(random.choice([400, 404, 500]), 'With best wishes from the chaos monkey.')


@app.before_first_request
def setup():
    from nomad import infrastructure

    if not app.config['TESTING']:
        infrastructure.setup()