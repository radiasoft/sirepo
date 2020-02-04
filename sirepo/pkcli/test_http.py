# -*- coding: utf-8 -*-
u"""async requests to server over http

:copyright: Copyright (c) 2020 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern import pkconfig
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp, pkdexc, pkdlog
import asyncio
import contextlib
import copy
import re
import sirepo.sim_data
import sirepo.util
import time
import tornado.httpclient
import random

CODES = PKDict(
    elegant=[
        PKDict(
            name='bunchComp - fourDipoleCSR',
            reports=[
                'bunchReport1',
                'elementAnimation10-5',
            ],
        ),
    ],
    srw=[
        PKDict(
            name='Tabulated Undulator Example',
            reports=[
                'fluxAnimation',
                'intensityReport',
                'multiElectronAnimation',
                'powerDensityReport',
                'sourceIntensityReport',
            ],
        ),
        PKDict(
            name='Bending Magnet Radiation',
            reports=[
                'beamline3DReport',
                'brillianceReport',
                'coherenceXAnimation',
                'coherenceYAnimation',
                'electronBeam',
                'fluxAnimation',
                'fluxReport',
                'initialIntensityReport',
                'intensityReport',
                'mirrorReport',
                'multiElectronAnimation',
                'powerDensityReport',
                'sourceIntensityReport',
                'trajectoryReport',
            ],
        ),
    ],
)

cfg = None


def default_command():
    _init()
    random.seed()
    asyncio.run(_run_all())


async def _cancel_on_exception(task):
    try:
        await task
    except Exception as e:
        task.cancel()
        raise


class _Client(PKDict):
    _global_lock = asyncio.Lock()
    _login_locks = PKDict()

    def __init__(self, **kwargs):
        super().__init__(
            _client=tornado.httpclient.AsyncHTTPClient(),
            _headers=PKDict({'User-Agent': 'test_http'}),
            **kwargs
        )

    def copy(self):
        n = type(self)()
        for k, v in self.items():
            if k != '_client':
                n[k] = copy.deepcopy(v)
        return n

    async def get(self, uri):
        uri = self._uri(uri)
        with _timer(uri):
            return self.parse_response(
                await self._client.fetch(
                    uri,
                    headers=self._headers,
                    method='GET',
                )
            )

    async def login(self):
        r = await self.post('/simulation-list', PKDict())
        assert r.srException.routeName == 'missingCookies'
        r = await self.post('/simulation-list', PKDict())
        assert r.srException.routeName == 'login'
        async with self._global_lock:
            self._login_locks.pksetdefault(self.email, asyncio.Lock())
        async with self._login_locks[self.email]:
            r = await self.post('/auth-email-login', PKDict(email=self.email))
            t = sirepo.util.create_token(
                self.email,
            ).decode()
            r = await self.post(
                self._uri('/auth-email-authorized/{}/{}'.format(self.sim_type, t)),
                data=PKDict(token=t, email=self.email),
            )
            assert r.state != 'srException', 'r={}'.format(r)
            if r.state == 'redirect' and 'complete' in r.uri:
                r = await self.post(
                    '/auth-complete-registration',
                    PKDict(displayName=self.email),
                )
        r = await self.post('/simulation-list', PKDict())
        self._sid = PKDict([(x.name, x.simulationId) for x in r])
        self._sim_db = PKDict()
        self._sim_data = sirepo.sim_data.get_class(self.sim_type)
        return self

    def parse_response(self, resp):
        self.resp = resp
        assert self.resp.code == 200, 'resp={}'.format(resp)
        self.json = None
        if 'Set-Cookie' in resp.headers:
            self._headers.Cookie = resp.headers['Set-Cookie']
        if 'json' in resp.headers['content-type']:
            self.json = pkjson.load_any(resp.body)
            return self.json
        try:
            b = resp.body.decode()
        except UnicodeDecodeError:
            # Binary data files can't be decoded
            return
        if 'html' in resp.headers['content-type']:
            m = re.search('location = "(/[^"]+)', b)
            if m:
                if 'error' in m.group(1):
                    self.json = PKDict(state='error', error='server error')
                else:
                    self.json = PKDict(state='redirect', uri=m.group(1))
                return self.json
        return b

    async def post(self, uri, data):
        data.simulationType = self.sim_type
        uri = self._uri(uri)
        with _timer(
                'uri={} sim_type={} report={}'.format(
                    uri,
                    data.simulationType,
                    data.get('report')
                ),
        ):
            return self.parse_response(
                await self._client.fetch(
                    uri,
                    body=pkjson.dump_bytes(data),
                    headers=self._headers.pksetdefault(
                        'Content-type',  'application/json'
                    ),
                    method='POST',
                    connect_timeout=1000000,
                    request_timeout=1000000,
                ),
            )

    async def sim_db(self, sim_name):
        try:
            return self._sim_db[sim_name]
        except KeyError:
            self._sim_db[sim_name] = await self.get(
                '/simulation/{}/{}/0'.format(
                    self.sim_type,
                    self._sid[sim_name],
                ),
            )
            return self._sim_db[sim_name]

    async def sim_run(self, name, report, timeout=90):

        async def _run(self):
            c = None
            i = self._sid[name]
            d = await self.sim_db(name)
            pkdlog('sid={} report={} state=start', i, report)
            r = await self.post(
                '/run-simulation',
                PKDict(
                    # works for sequential simulations, too
                    forceRun=True,
                    models=d.models,
                    report=report,
                    simulationId=i,
                    simulationType=self.sim_type,
                ),
            )
            try:
                p = self._sim_data.is_parallel(report)
                if r.state == 'completed':
                    return
                c = r.get('nextRequest')
                for _ in range(timeout):
                    if r.state in ('completed', 'error'):
                        c = None
                        break
                    r = await self.post('/run-status', r.nextRequest)
                    await asyncio.sleep(1)
                else:
                    pkdlog('sid={} report={} timeout={}', i, report, timeout)
            except asyncio.CancelledError:
                return
            except Exception:
                pkdlog('r={}', r)
                raise
            finally:
                if c:
                    await self.post('/run-cancel', c)
                s = 'cancel' if c else r.get('state')
                e = False
                if s == 'error':
                    e = True
                    s = r.get('error', '<unknown error>')
                pkdlog('sid={} report={} state={}', i, report, s)
                assert not e, \
                    'unexpected error state, error={} sid={}, report={}'.format(s, i, report)
            if p:
                g = self._sim_data.frame_id(d, r, report, 0)
                f = await self.get('/simulation-frame/' + g)
                assert 'title' in f, \
                    'no title in frame={}'.format(f)
                await self.get(
                    '/download-data-file/{}/{}/{}/{}'.format(
                        self.sim_type,
                        i,
                        report,
                        0,
                    ),
                )
                c = None
                try:
                    c = await self.post(
                        '/run-simulation',
                        PKDict(
                            # works for sequential simulations, too
                            forceRun=True,
                            models=d.models,
                            report=report,
                            simulationId=i,
                            simulationType=self.sim_type,
                        ),
                    )
                    f = await self.get('/simulation-frame/' + g)
                    assert f.state == 'error', \
                        'expecting error instead of frame={}'.format(f)
                except asyncio.CancelledError:
                    return
                finally:
                    if c:
                        await self.post('/run-cancel', c.get('nextRequest'))
        return await _run(self.copy())

    def _uri(self, uri):
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


async def _run(email, sim_type):
    await _run_sequential_parallel(
        await _Client(email=email, sim_type=sim_type).login(),
    )


async def _run_all():
    l = []
    for a in (
        ('a@b.c', 'srw',),
        ('a@b.c', 'elegant'),
    ):
        l.append(_run(*a))
    await _cancel_on_exception(asyncio.gather(*l))


async def _run_sequential_parallel(client):
    c = []
    s = CODES[client.sim_type]
    e = s[random.randrange(len(s))]
    random.shuffle(e.reports)
    for r in e.reports:
        c.append(client.sim_run(e.name, r))
    await _cancel_on_exception(asyncio.gather(*c))


@contextlib.contextmanager
def _timer(description):
    s = time.time()
    yield
    if 'run-status' not in description:
        pkdlog('{} elapsed_time={}', description, time.time() - s)
