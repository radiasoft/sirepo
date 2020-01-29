# -*- coding: utf-8 -*-
u"""multi-threaded requests to server over http

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdlog, pkdp, pkdexc, pkdc
import copy
import re
import requests
import subprocess
import threading
import time


cfg = None


def run_all():
    l = []
    for a in (
#        ('a@b.c', 'myapp', 'Scooby Doo'),
        ('a@b.c', 'srw', "Young's Double Slit Experiment"),
    ):
        t = threading.Thread(target=run, args=a)
        l.append(t)
        t.start()
    for t in l:
        t.join()


def run(email, sim_type, *sim_names):
    run_sequential_parallel(_Client(email=email, sim_type=sim_type).login())
    '''
    o = list(sim_names)
    for x in l:
        if x.name in o:
            o.remove(x.name)
    assert not o, \
        'sim_names={} not found in list={}'.format(o, l)
    d = s.get(
        '/simulation/{}/{}/0'.format(s.sim_type, x.simulationId),
    )
    x = d.models.simulation
    pkdlog('sid={} name={}', x.simulationId, x.name)
    '''


def run_sequential_parallel(client):
    #t = client.sim_run("Young's Double Slit Experiment", 'multiElectronAnimation')
    t = client.sim_run("Young's Double Slit Experiment", 'intensityReport')
    t.join()
#        'brillianceReport',
    #     'fluxReport',
    #     'initialIntensityReport',
    #     'intensityReport',
    #     'powerDensityReport',
    #     'sirepo-data.json',
    #     'sourceIntensityReport',
    #     'trajectoryReport',
    #     'watchpointReport6',
    #     'watchpointReport7',
    # ):




class _Client(PKDict):

    __global_lock = threading.Lock()

    __login_locks = PKDict()

    def __init__(self, **kwargs):
        super(_Client, self).__init__(**kwargs)
        _init()
        self._session = requests.Session()
        self._session.verify = False

    def copy(self):
        n = type(self)()
        # reaches inside requests.Session
        n._session.cookies = self._session.cookies.copy()
        for k, v in self.items():
            if k not in n:
                n[k] = copy.deepcopy(v)
        return n

    def get(self, uri):
        return self.parse_response(
            self._session.get(url=self.uri(uri)),
        )

    def login(self):
        r = self.post('/simulation-list', PKDict())
        assert r.srException.routeName == 'missingCookies'
        r = self.post('/simulation-list', PKDict())
        assert r.srException.routeName == 'login'
        with self.__global_lock:
            self.__login_locks.pksetdefault(self.email, threading.Lock)
        with self.__login_locks[self.email]:
            r = self.post('/auth-email-login', PKDict(email=self.email))
            r = self.post(
                r.url,
                data=PKDict(token=r.url.split('/').pop(), email=self.email),
            )
            m = re.search('location = "(/[^"]+)', r)
            if m and 'complete' in m.group(1):
                r = self.post(
                    '/auth-complete-registration',
                    PKDict(displayName=self.email),
                )

        r = self.post('/simulation-list', PKDict())
        self._sid = PKDict([(x.name, x.simulationId) for x in r])
        self._sim_data = PKDict()
        return self

    def parse_response(self, resp):
        resp.raise_for_status()
        if 'json' in resp.headers['content-type']:
            return pkjson.load_any(resp.content)
        return resp.content

    def post(self, uri, data):
        data.simulationType = self.sim_type
        return self.parse_response(
            self._session.post(
                url=self.uri(uri),
                data=pkjson.dump_bytes(data),
                headers=PKDict({'Content-type': 'application/json'}),
            ),
        )

    def sim_data(self, sim_name):
        return self._sim_data.pksetdefault(
            sim_name,
            lambda: self.get(
                '/simulation/{}/{}/0'.format(self.sim_type, self._sid[sim_name]),
            ),
        )[sim_name]

    def sim_run(self, name, report, timeout=10):

        def _run(client):
            c = None
            i = client._sid[name]
            r = client.post(
                '/run-simulation',
                PKDict(
                    models=client.sim_data(name).models,
                    report=report,
                    simulationId=i,
                    simulationType=client.sim_type,
                ),
            )
            try:
                if r.state == 'completed':
                    return
                c = r.get('nextRequest')
                for _ in range(timeout):
                    pkdp('here')
                    if r.state in ('completed', 'error'):
                        c = None
                        break
                    r = self.post('/run-status', r.nextRequest)
                    pkdp(r.state)
                    time.sleep(1)
                else:
                    pkdlog('sid={} report={} timeout={}', i, report, timeout)
            finally:
                if c:
                    self.post('/run-cancel', c)
                pkdlog('sid={} report={} state={}', i, report, 'cancel' if c else r.state)

        t = threading.Thread(target=_run, args=[self.copy()])
        t.start()
        return t


    def uri(self, uri):
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
