# -*- coding: utf-8 -*-
u"""support for oauth test

:copyright: Copyright (c) 2019 RadiaSoft LLC, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function

class MockOAuthClient(object):

    def __init__(self, monkeypatch, user_name='joeblow'):
        from pykern import pkcollections
        from sirepo.auth import github

        self.values = pkcollections.Dict(
            access_token='xyzzy',
            data=pkcollections.Dict(
                # don't really care about id as long as it is bound to login
                id=user_name,
                login=user_name,
            ),
        )
        monkeypatch.setattr(github, '_oauth_client', self)

    def __call__(self, *args, **kwargs):
        return self

    def authorize(self, callback, state):
        from sirepo.auth import github
        import flask

        self.values.callback = callback
        self.values.state = state
        return flask.redirect(
            'https://github.com/login/oauth/oauthorize?response_type=code&client_id={}&redirect_uri={}&state={}'.format(
                github.cfg.key,
                github.cfg.callback_uri,
                state,
            ),
            code=302,
        )

    def authorized_response(self, *args, **kwargs):
        return self.values

    def get(self, *args, **kwargs):
        return self.values
