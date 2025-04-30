"""Requests hold context for API calls

:copyright: Copyright (c) 2019-2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import contextlib
import copy
import dns.resolver
import dns.reversename
import pykern.quest
import sirepo.api_perm
import sirepo.modules
import sirepo.uri
import sirepo.util
import re


_PARENT_ATTR = "parent"

_SIM_TYPE_ATTR = "sim_type"

_SPEC_ATTR = "quest_spec"

_SPEC_SIM_TYPE_CONST = re.compile(r"\s*SimType\s+const=(\S+)")


@contextlib.contextmanager
def start(in_pkcli=False):
    auth = sirepo.modules.import_and_init("sirepo.auth")
    qcall = API(in_pkcli=in_pkcli)
    c = False
    try:
        auth.init_quest(qcall)
        yield qcall
        c = True
    finally:
        qcall.destroy(commit=c)


class API(pykern.quest.API):
    """Holds request context for all API calls."""

    def __init__(self, in_pkcli=False):
        super().__init__()
        _Bucket(self)
        self.bucket_set("in_pkcli", in_pkcli)

    def absolute_uri(self, uri):
        """Convert to an absolute uri

        Args:
            uri (str): must begin with "/"
        Returns:
            str: absolute uri
        """
        assert uri[0] == "/"
        return self.sreq.http_server_uri + uri[1:]

    def attr_set(self, name, obj):
        """Assign an object to qcall"""
        assert isinstance(obj, Attr)
        assert name not in self
        self[name] = obj

    def bucket_get(self, name):
        return self._bucket[name]

    def bucket_get_or_default(self, name, default):
        """Get named value or pksetdefault

        Args:
            name (str): key
            default (object): if callable, will be called
        Returns:
            object: value of name
        """
        return self._bucket.pksetdefault(name, default)[name]

    def bucket_set(self, name, value):
        assert (
            name not in self._bucket
        ), f"duplicate name={name} in _bucket={list(self._bucket.keys())}"
        self._bucket[name] = value

    def bucket_unchecked_get(self, name):
        return self._bucket.get(name)

    async def call_api(self, name, kwargs=None, body=None):
        """Calls uri_router.call_api, which calls the API with permission checks.

        Args:
            name (object): api name (without `api_` prefix)
            kwargs (PKDict): to be passed to API [None]
            body (PKDict): will be returned `self.body_as_dict` [None]
        Returns:
            Reply: result
        """
        if body is not None and not isinstance(body, PKDict):
            raise AssertionError(f"invalid body type={type(body)} body={body}")
        return await uri_router.call_api(self, name, kwargs=kwargs, body=body)

    def call_api_sync(self, *args, **kwargs):
        """Synchronous call_api

        Only use in tests.
        """
        import asyncio

        return asyncio.run(self.call_api(*args, **kwargs))

    def destroy(self, commit=False):
        for k, v in reversed(list(self.items())):
            if hasattr(v, "destroy"):
                try:
                    v.destroy(commit=commit)
                except Exception:
                    pkdlog("destroy failed attr={} stack={}", v, pkdexc())
            self.pkdel(k)

    def headers_for_cache(self, resp, path=None):
        return resp.headers_for_cache(path)

    def headers_for_no_cache(self, resp):
        return resp.headers_for_no_cache()

    def parent_set(self, parent):
        """Links parent qcall to self and copies Attrs

        Args:
            parent (API): qcall to link as parent
        """
        if not isinstance(parent, API):
            raise AssertionError(f"invalid parent type={type(parent)}")
        # must be right after initialization
        if not (len(self._bucket.keys()) == 1 and len(self.keys()) == 2):
            raise AssertionError(f"must be first call after __init__; child={self}")
        # In insertion order so already sorted topologically. _bucket will
        # be reinitialized, but it knows that.
        for k, v in parent.items():
            if k == "_destroyed":
                continue
            if k == "_bucket":
                self._bucket.init_bucket_for_child(parent)
                continue
            if k in self:
                raise AssertionError(f"Attr={k} already in child={self}")
            if not hasattr(v, "init_quest_for_child"):
                # Only copy Attr items
                continue
            v.init_quest_for_child(child=self, parent=parent)
            if self[k] is v:
                raise AssertionError(f"Attr={k} must be unique object for child")

    def body_as_dict(self):
        return self.sreq.body_as_dict()

    def parse_params(self, **kwargs):
        return http_request.parse_post(
            self,
            PKDict(kwargs).pksetdefault(req_data=PKDict),
        )

    def parse_post(self, **kwargs):
        return http_request.parse_post(self, PKDict(kwargs))

    def reply(self, **kwargs):
        return self.sreply.from_kwargs(**kwargs)

    def reply_as_proxy(self, content, content_type):
        return self.sreply.from_kwargs(
            content=content,
            content_type=content_type,
        ).headers_for_no_cache()

    def reply_attachment(self, content_or_path, filename=None):
        return self.sreply.gen_attachment(
            content_or_path=content_or_path,
            filename=filename,
        )

    def reply_dict(self, value):
        return self.sreply.gen_dict(value)

    def reply_file(self, path, filename=None):
        return self.sreply.gen_file(path=path, filename=filename)

    def reply_html(self, path):
        return self.sreply.render_html(path)

    def reply_list_deprecated(self, value):
        """Always reply_dict, not with a list"""
        return self.sreply.gen_list_deprecated(value)

    def reply_ok(self, value=None):
        return self.sreply.gen_dict_ok(value)

    def reply_redirect(self, uri):
        return self.sreply.gen_redirect(uri)

    def reply_redirect_for_app_root(self, sim_type=None):
        return self.reply_redirect(self.uri_for_app_root(sim_type))

    def reply_redirect_for_local_route(
        self,
        sim_type=None,
        route=None,
        params=None,
        query=None,
        **kwargs,
    ):
        return self.sreply.gen_redirect_for_local_route(
            sim_type=sim_type,
            route=route,
            params=params,
            query=query,
            **kwargs,
        )

    def reply_static_jinja(self, base, ext, j2_ctx):
        return self.sreply.render_static_jinja(base, ext, j2_ctx)

    def sim_type_set(self, sim_type):
        """Set sim_type if there, else don't set"""
        if not sirepo.util.is_sim_type(sim_type):
            # Don't change sim_type unless we have a valid one
            return
        # Don't change once set
        if _SIM_TYPE_ATTR in self:
            return
        self._bucket[_SIM_TYPE_ATTR] = sim_type

    def sim_type_set_from_spec(self, func):
        s = getattr(func, _SPEC_ATTR).sim_type
        if s:
            self.sim_type_set(s)

    def sim_type_uget(self, value=None):
        """Return value or reuqest's sim_type

        Args:
            value (str): will be validated if not None
        Returns:
            str: sim_type or possibly None
        """
        if value:
            return sirepo.util.assert_sim_type(value)
        return self._bucket.get(_SIM_TYPE_ATTR)

    def uri_for_api(self, api_name, params=None):
        """Generate uri for api method

        Args:
            api_name (str): full name of api
            params (PKDict): paramters to pass to uri
        Returns:
            str: formmatted URI
        """
        return uri_router.uri_for_api(api_name=api_name, params=params)

    def uri_for_app_root(self, sim_type=None):
        """Return uri for sim_type

        Args:
            sim_type (str): sim_type (must be defined)
        Returns:
            str: uri
        """
        return sirepo.uri.app_root(sim_type=self.sim_type_uget(sim_type))

    def user_agent_headers(self):
        def _dns_reverse_lookup(ip):
            try:
                if ip:
                    return ", ".join(
                        [
                            str(i)
                            for i in dns.resolver.resolve(
                                dns.reversename.from_address(ip), "PTR"
                            ).rrset.items
                        ]
                    )
            # 127.0.0.1 is not reverse mapped, resulting in dns.resolver.NoNameservers exception
            except (
                dns.resolver.NoAnswer,
                dns.resolver.NXDOMAIN,
                dns.resolver.NoNameservers,
            ):
                pass
            return "No Reverse DNS Lookup"

        return PKDict(
            ip_addr=self.sreq.remote_addr,
            domain_name=_dns_reverse_lookup(self.sreq.remote_addr),
            user_agent=self.sreq.header_uget("User-Agent"),
        )


class Attr(PKDict):
    _INIT_QUEST_FOR_CHILD_KEYS = frozenset()

    # Class names bound to attribute keys
    _KEY_MAP = PKDict(
        _Auth="auth",
        _AuthDb="auth_db",
        # bucket should only be referred to by bucket_get/set
        _Bucket="_bucket",
        _Cookie="cookie",
        _SReply="sreply",
        _SRequestCLI="sreq",
        _SRequestHTTP="sreq",
        _SRequestWebSocket="sreq",
    )

    def __init__(self, qcall, init_quest_for_child=False, **kwargs):
        """Initialize object from a parent or a new qcall

        Args:
            qcall (API): what qcall is being initialized
            init_quest_for_child (bool): True if called from `init_quest_for_child`
            kwargs (dict): insert into dictionary
        """
        super().__init__(qcall=qcall, **kwargs)
        qcall.attr_set(self._key(), self)

    def detach_from_quest(self):
        """Useful only for `_SReply`

        Detaches from the quest so won't be destroyed.

        Returns:
            self: object
        """
        self.qcall.pkdel(self._key())
        self.qcall = None
        return self

    def init_quest_for_child(self, child, parent):
        """Create or copy state of `self` (parent) to child (return)

        `self` is the Attr in `parent`

        If sharing between parent and child, care should be taken.

        Args:
            child (API): child quest that is being initialized
            parent (API): parent quest to initialize from

        Returns:
            Attr: instance to be assigned to `child`
        """
        rv = self.__class__(qcall=child, init_quest_for_child=True)
        for k, v in parent[self._key()].items():
            if k not in self._INIT_QUEST_FOR_CHILD_KEYS:
                continue
            if isinstance(v, (API, Attr)):
                raise AssertionError(
                    f"invalid value type={type(v)} key={k} self={self}"
                )
            rv[k] = copy.deepcopy(v)
        return rv

    def _key(self):
        return self._KEY_MAP[self.__class__.__name__]


class Spec(pykern.quest.Spec):
    def __init__(self, perm, **kwargs):
        self.perm = perm
        self.kwargs = PKDict(kwargs)
        self.sim_type = None
        m = _SPEC_SIM_TYPE_CONST.search(self.kwargs.get("sim_type") or "")
        self.sim_type = m.group(1) if m else None
        super().__init__()

    # TODO(robnagler) put this in super and just setattr perm.
    def __call__(self, func):
        def _wrapper(*args, **kwargs):
            return self.func(*args, **kwargs)

        self.func = func
        setattr(
            _wrapper,
            sirepo.api_perm.ATTR,
            getattr(sirepo.api_perm.APIPerm, self.perm.upper()),
        )
        setattr(_wrapper, _SPEC_ATTR, self)
        return _wrapper


class _Bucket(Attr):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Don't want a backlink here, because we expect exact count of items
        self.pkdel("qcall")

    def init_bucket_for_child(self, parent):
        """Initializes already created `_bucket` attr"""
        self[_PARENT_ATTR] = parent
        self.in_pkcli = parent.bucket_get("in_pkcli")


def init_module(**imports):
    import sirepo.util

    # import http_request, uri_router, simulation_db
    sirepo.util.setattr_imports(imports)
