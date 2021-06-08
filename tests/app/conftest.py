#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import pytest
from fastapi.testclient import TestClient

from nomad.app.main import app
from nomad.datamodel import User
from nomad.app.v1.routers.auth import generate_upload_token


def create_auth_headers(user: User):
    return {
        'Authorization': 'Bearer %s' % user.user_id
    }


@pytest.fixture(scope='module')
def test_user_auth(test_user: User):
    return create_auth_headers(test_user)


@pytest.fixture(scope='module')
def other_test_user_auth(other_test_user: User):
    return create_auth_headers(other_test_user)


@pytest.fixture(scope='module')
def admin_user_auth(admin_user: User):
    return create_auth_headers(admin_user)


@pytest.fixture(scope='module')
def test_users_dict(test_user, other_test_user, admin_user):
    return {
        'test_user': test_user,
        'other_test_user': other_test_user,
        'admin_user': admin_user}


@pytest.fixture(scope='module')
def test_auth_dict(
        test_user, other_test_user, admin_user,
        test_user_auth, other_test_user_auth, admin_user_auth):
    '''
    Returns a dictionary of the form {user_name: (auth_headers, token)}. The key 'invalid'
    contains an example of invalid credentials, and the key None contains (None, None).
    '''
    return {
        'test_user': (test_user_auth, generate_upload_token(test_user)),
        'other_test_user': (other_test_user_auth, generate_upload_token(other_test_user)),
        'admin_user': (admin_user_auth, generate_upload_token(admin_user)),
        'invalid': ({'Authorization': 'Bearer JUST-MADE-IT-UP'}, 'invalid.token'),
        None: (None, None)}


@pytest.fixture(scope='session')
def client():
    return TestClient(app, base_url='http://testserver/')
