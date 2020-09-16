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
        from sirepo.auth import github

        self.values = pkcollections.Dict(
            access_token='xyzzy',
            user=pkcollections.Dict(
                # don't really care about id as long as it is bound to login
                id=user_name,
                login=user_name,
            ),
        )
        monkeypatch.setattr(github, '_client', self)

    def __call__(self, *args, **kwargs):
        return self

    def authorize_redirect(self, redirect_uri, state):
        from sirepo.auth import github
        import sirepo.http_reply

        self.values.redirect_uri = redirect_uri
        self.values.state = state
        return sirepo.http_reply.gen_redirect(
            'https://github.com/login/oauth/oauthorize?response_type=code&client_id={}&redirect_uri={}&state={}'.format(
                github.cfg.key,
                github.cfg.callback_uri,
                state,
            ),
        )

    def authorize_access_token(self, *args, **kwargs):
        return self.values

    def get(self, *args, **kwargs):
        return _JSON(self.values[args[0]])


class _JSON(PKDict):

    def json(self):
        return self
