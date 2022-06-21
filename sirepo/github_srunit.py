# -*- coding: utf-8 -*-
u"""support for oauth test

:copyright: Copyright (c) 2019 RadiaSoft LLC, Inc.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict


class MockOAuthClient(object):

    def __init__(self, monkeypatch, user_name='joeblow'):
        from pykern import pkcollections
        import sirepo.oauth

        self.values = PKDict({
            'access_token': 'xyzzy',
            'https://api.github.com/user': PKDict(
                # don't really care about id as long as it is bound to login
                id=user_name,
                login=user_name,
            ),
        })
        monkeypatch.setattr(sirepo.oauth, '_client', self)

    def __call__(self, *args, **kwargs):
        return self


    def authorize_access_token(self, *args, **kwargs):
        return self.values

    def create_authorization_url(self, *args, **kwargs):
        from sirepo.auth import github
        import sirepo.http_reply

        r = github.cfg.callback_uri
        self.values.redirect_uri = r
        self.values.state = 'xxyyzz'
        return f'https://github.com/login/oauth/oauthorize?response_type=code&client_id={github.cfg.key}&redirect_uri={r}&state={self.values.state}', self.values.state

    def fetch_token(self, *args, **kwargs):
        return 'a_mock_token'

    def get(self, *args, **kwargs):
        return _JSON(self.values[args[0]])


class _JSON(PKDict):

    def json(self):
        return self
