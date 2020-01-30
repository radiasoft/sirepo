from pykern import pkconfig
from pykern import pkjson
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import asyncio
import re
import sirepo.sim_data
import sirepo.util
import tornado.httpclient

cfg = None

def main():
    asyncio.run(run_all())


async def run_all():
    l = []
    for a in (
#        ('a@b.c', 'myapp', 'Scooby Doo'),
        ('a@b.c', 'srw', "Young's Double Slit Experiment"),
    ):
        # t = threading.Thread(target=run, args=a)
        l.append(run(*a))
    await asyncio.gather(*l)


async def run(email, sim_type, *sim_names):
    c = await _Client(email=email, sim_type=sim_type).login()


class _Client(PKDict):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        _init()
        # TODO(e-carlin): assign as part of pkdict super creation
        self._client = tornado.httpclient.AsyncHTTPClient()
        self._cookie = PKDict()

    async def login(self):
        r = await self.post('/simulation-list', PKDict())
        assert r.srException.routeName == 'missingCookies'
        r = await self.post('/simulation-list', PKDict())
        assert r.srException.routeName == 'login'
        # # with self.__global_lock:
        # #     self.__login_locks.pksetdefault(self.email, threading.Lock)
        # # with self.__login_locks[self.email]:
        r = await self.post('/auth-email-login', PKDict(email=self.email))
        t = sirepo.util.create_token(self.email)
        pkdp('eeeeeeeeeee')
        r = await self.post(
            self._uri('/auth-email-authorized/{}/{}'.format(self.sim_type, t)),
            data=PKDict(token=t, email=self.email),
        )
        # if r.state == 'redirect' and 'complete' in r.uri:
        #     r = self.post(
        #         '/auth-complete-registration',
        #         PKDict(displayName=self.email),
        #     )
        # r = self.post('/simulation-list', PKDict())
        # self._sid = PKDict([(x.name, x.simulationId) for x in r])
        # self._sim_db = PKDict()
        # self._sim_data = sirepo.sim_data.get_class(self.sim_type)
        return self

    def parse_response(self, resp):
        self.resp = resp
        self.json = None
        if 'Set-Cookie' in resp.headers:
            self._cookie = PKDict(
                cookie=resp.headers['Set-Cookie'],
            )
        if 'json' in resp.headers['content-type']:
            self.json = pkjson.load_any(resp.body)
            return self.json
        b = resp.body.decode('utf-8')
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
        return self.parse_response(
            await self._client.fetch(
                self._uri(uri),
                headers=PKDict(
                    {'Content-type': 'application/json'},
                    **self._cookie,
                ),
                method='POST',
                body=pkjson.dump_bytes(data),
            )
        )

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
