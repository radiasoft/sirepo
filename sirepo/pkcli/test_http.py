# -*- coding: utf-8 -*-
u"""test driver for remote tests
:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern import pkconfig
from pykern import pkjson
from pykern.pkdebug import pkdlog, pkdp, pkdexc, pkdc
import re
import requests
import subprocess
import threading


cfg = None


def run_all():
    l = []
    for a in (
        ('a@b.c', 'myapp', 'Scooby Doo'),
        ('a@b.c', 'srw', "Young's Double Slit Experiment"),
    ):
        t = threading.Thread(target=run, args=a)
        l.append(t)
        t.start()
    for t in l:
        t.join()


def run(email, sim_type, sim_name):
    s = _Session(email, sim_type)
    l = s.sr_login()
    for x in l:
        if x.name == sim_name:
            break
    else:
        raise AssertionError(
            'sim_name={} not found in list={}'.format(sim_name, l),
        )
    d = s.sr_get(
        '/simulation/{}/{}/0'.format(s.sr_sim_type, x.simulationId),
    )
    pkdp(d)



class _Session(requests.Session):

    __global_lock = threading.Lock()

    __login_locks = PKDict()

    def __init__(self, email, sim_type):
        super(_Session, self).__init__()
        _init()
        self.sr_email = email
        self.sr_sim_type = sim_type

    def sr_get(self, uri):
        return self.sr_parse_response(
            self.get(
                url=self.sr_uri(uri),
                verify=False,
            ),
        )

    def sr_login(self):
        self.sr_get('/' + self.sr_sim_type)
        r = self.sr_post('/simulation-list', PKDict())
        with self.__global_lock:
            self.__login_locks.pksetdefault(self.sr_email, threading.Lock)
        with self.__login_locks[self.sr_email]:
            r = self.sr_post('/auth-email-login', PKDict(email=self.sr_email))
            r = self.sr_post(
                r.url,
                data=PKDict(token=r.url.split('/').pop(), email=self.sr_email),
            )
            m = re.search('location = "(/[^"]+)', r)
            if m and 'complete' in m.group(1):
                r = self.sr_post(
                    '/auth-complete-registration',
                    PKDict(displayName=self.sr_email),
                )
        return self.sr_post('/simulation-list', PKDict())

    def sr_parse_response(self, resp):
        resp.raise_for_status()
        if 'json' in resp.headers['content-type']:
            return pkjson.load_any(resp.content)
        return resp.content

    def sr_post(self, uri, data):
        data.simulationType = self.sr_sim_type
        return self.sr_parse_response(
            self.post(
                url=self.sr_uri(uri),
                data=pkjson.dump_bytes(data),
                headers=PKDict({'Content-type': 'application/json'}),
                verify=False,
            ),
        )

    def sr_uri(self, uri):
        if uri.startswith('http'):
            return uri
        assert uri.startswith('/')
        return cfg.server_uri + uri

def _init():
    global cfg
    if cfg:
        return
    cfg = pkconfig.init(
        server_uri=('http://127.0.0.1:8000', str, 'where to send requests'),
    )
