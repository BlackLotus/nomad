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

from flask_restplus import abort, Resource

from nomad import infrastructure, config

from .api import api
from .auth import authenticate


ns = api.namespace('admin', description='Administrative operations')


@ns.route('/reset')
class AdminResetResource(Resource):
    @api.doc('exec_reset_command')
    @api.response(200, 'Reset performed')
    @api.response(400, 'Reset not available/disabled')
    @authenticate(admin_only=True)
    def post(self):
        """
        The ``reset`` command will attempt to clear the contents of all databased and
        indices.

        Nomad can be configured to disable reset and the command might not be available.
        """
        if config.services.disable_reset:
            abort(400, message='Operation is disabled')

        infrastructure.reset()

        return dict(messager='Reset performed.'), 200


@ns.route('/remove')
class AdminRemoveResource(Resource):
    @api.doc('exec_remove_command')
    @api.response(200, 'Remove performed')
    @api.response(400, 'Remove not available/disabled')
    @authenticate(admin_only=True)
    def post(self):
        """
        The ``remove``command will attempt to remove all databases. Expect the
        api to stop functioning after this request.

        Nomad can be configured to disable remove and the command might not be available.
        """

        if config.services.disable_reset:
            abort(400, message='Operation is disabled')

        infrastructure.remove()

        return dict(messager='Remove performed.'), 200
