# -*- coding: utf-8 -*-
"""Authentication

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo import events
from sirepo import http_reply
from sirepo import job
from sirepo import util
import contextlib
import datetime
import importlib
import pyisemail
import sirepo.auth_db
import sirepo.auth_role
import sirepo.cookie
import sirepo.events
import sirepo.feature_config
import sirepo.quest
import sirepo.request
import sirepo.session
import sirepo.template
import sirepo.uri
import sirepo.util


#: what routeName to return in the event user is logged out in require_user
LOGIN_ROUTE_NAME = "login"

#: Email is used by moderation. Do not use this var, use qcall.auth.METHOD_EMAIL
METHOD_EMAIL = "email"

#: Guest is a special method. Do not use this var, use qcall.auth.METHOD_GUEST
METHOD_GUEST = "guest"

#: key for auth method for login state
_COOKIE_METHOD = "sram"

#: There will always be this value in the cookie, if there is a cookie
_COOKIE_STATE = "sras"

#: Identifies the user in the cookie
_COOKIE_USER = "srau"

_GUEST_USER_DISPLAY_NAME = "Guest User"

_PAYMENT_PLAN_BASIC = "basic"
_PAYMENT_PLAN_ENTERPRISE = sirepo.auth_role.ROLE_PAYMENT_PLAN_ENTERPRISE
_PAYMENT_PLAN_PREMIUM = sirepo.auth_role.ROLE_PAYMENT_PLAN_PREMIUM
_ALL_PAYMENT_PLANS = (
    _PAYMENT_PLAN_BASIC,
    _PAYMENT_PLAN_ENTERPRISE,
    _PAYMENT_PLAN_PREMIUM,
)

_STATE_LOGGED_IN = "li"
_STATE_LOGGED_OUT = "lo"
_STATE_COMPLETE_REGISTRATION = "cr"

#: name to module object
_METHOD_MODULES = pkcollections.Dict()

# TODO(robnagler) probably from the schema
#: For formatting the size parameter to an avatar_uri
_AVATAR_SIZE = 40

#: methods + deprecated_methods
valid_methods = None

#: Methods that the user is allowed to see
visible_methods = None

#: visible_methods excluding guest
non_guest_methods = None

_cfg = None


def hack_logged_in_user():
    # avoids case of no quest (sirepo.agent)
    return _cfg.logged_in_user or sirepo.quest.hack_current().auth.logged_in_user()


def init_quest(qcall):
    o = _Auth(qcall=qcall)
    qcall.attr_set("auth", o)
    sirepo.auth_db.init_quest(qcall)
    if not _cfg.logged_in_user and sirepo.flask.in_request():
        sirepo.request.init_quest(qcall)
        # TODO(robnagler): process auth basic header, too. this
        # should not cookie but route to auth_basic.
        sirepo.cookie.init_quest(qcall)
        # TODO(robnagler) auth_db
        o._set_log_user()
        sirepo.session.init_quest(qcall)


def init_module(**imports):
    global _cfg

    def _init_full():
        global visible_methods, valid_methods, non_guest_methods

        simulation_db.hook_auth_user = hack_logged_in_user
        p = pkinspect.this_module().__name__
        visible_methods = []
        valid_methods = _cfg.methods.union(_cfg.deprecated_methods)
        for n in valid_methods:
            m = importlib.import_module(pkinspect.module_name_join((p, n)))
            _METHOD_MODULES[n] = m
            if m.AUTH_METHOD_VISIBLE and n in _cfg.methods:
                visible_methods.append(n)
        visible_methods = tuple(sorted(visible_methods))
        non_guest_methods = tuple(m for m in visible_methods if m != METHOD_GUEST)
        s = list(simulation_db.SCHEMA_COMMON.common.constants.paymentPlans.keys())
        assert sorted(s) == sorted(
            _ALL_PAYMENT_PLANS
        ), f"payment plans from SCHEMA_COMMON={s} not equal to _ALL_PAYMENT_PLANS={_ALL_PAYMENT_PLANS}"

    if _cfg:
        return
    # import simulation_db
    sirepo.util.setattr_imports(imports)
    _cfg = pkconfig.init(
        methods=((METHOD_GUEST,), set, "for logging in"),
        deprecated_methods=(set(), set, "for migrating to methods"),
        logged_in_user=(None, str, "Only for sirepo.job_supervisor"),
    )
    if _cfg.logged_in_user:
        _cfg.deprecated_methods = frozenset()
        _cfg.methods = frozenset((METHOD_GUEST,))
    else:
        _init_full()


def only_for_api_method_modules():
    return list(_METHOD_MODULES.values())


class _Auth(sirepo.quest.Attr):
    METHOD_EMAIL = METHOD_EMAIL
    METHOD_GUEST = METHOD_GUEST

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logged_in_user = _cfg.logged_in_user
        self._logged_in_method = METHOD_GUEST if _cfg.logged_in_user else None

    def check_sim_type_role(self, sim_type):
        from sirepo import auth_role_moderation, oauth, uri_router

        t = sirepo.template.assert_sim_type(sim_type)
        self.qcall.sim_type_set(t)
        if t not in sirepo.feature_config.auth_controlled_sim_types():
            return
        if not uri_router.maybe_sim_type_required_for_api(self.qcall):
            return
        u = self.logged_in_user()
        r = sirepo.auth_role.for_sim_type(t)
        if sirepo.auth_db.UserRole.has_role(
            u, r
        ) and not sirepo.auth_db.UserRole.is_expired(u, r):
            return
        elif r in sirepo.auth_role.for_proprietary_oauth_sim_types():
            oauth.raise_authorize_redirect(self.qcall, sirepo.auth_role.sim_type(r))
        if r in sirepo.auth_role.for_moderated_sim_types():
            auth_role_moderation.raise_control_for_user(self.qcall, u, r, t)
        sirepo.util.raise_forbidden(f"uid={u} does not have access to sim_type={t}")

    def complete_registration(self, name=None):
        """Update the database with the user's display_name and sets state to logged-in.
        Guests will have no name.
        """
        u = self._qcall_bound_user()
        with sirepo.util.THREAD_LOCK:
            r = self.user_registration(u)
            if self._qcall_bound_method() == METHOD_GUEST and name is not None:
                raise AssertionError(
                    "user name={name} should be None with method={METHOD_GUEST}",
                )
            r.display_name = name
            r.save()
        self.qcall.cookie.set_value(_COOKIE_STATE, _STATE_LOGGED_IN)

    def cookie_cleaner(self, values):
        """Migrate from old cookie values

        Always sets _COOKIE_STATE, which is our sentinel.

        Args:
            values (dict): just parsed values
        Returns:
            dict: unmodified or migrated values
        """
        if values.get(_COOKIE_STATE):
            # normal case: we've seen a cookie at least once
            # check for _cfg.methods changes
            m = values.get(_COOKIE_METHOD)
            if m and m not in valid_methods:
                # invalid method (changed config), reset state
                pkdlog(
                    "possibly misconfigured server: invalid cookie_method={}, clearing values={}",
                    m,
                    values,
                )
                pkcollections.unchecked_del(
                    values,
                    _COOKIE_METHOD,
                    _COOKIE_USER,
                    _COOKIE_STATE,
                )
            return values
        # data cleaning; do not need auth old values
        if values.get("sru") or values.get("uid"):
            pkdlog("unknown cookie values, clearing, not migrating: {}", values)
            return {}
        # normal case: new visitor, and no user/state; set logged out
        # and return all values
        values[_COOKIE_STATE] = _STATE_LOGGED_OUT
        return values

    def create_user(self, uid_generated_callback, module):
        u = simulation_db.user_create()
        uid_generated_callback(u)
        self._create_roles_for_new_user(u, module.AUTH_METHOD)
        return u

    def get_module(self, name):
        return _METHOD_MODULES[name]

    def guest_uids(self):
        """All of the uids corresponding to guest users."""
        return sirepo.auth_db.UserRegistration.search_all_for_column(
            "uid", display_name=None
        )

    def is_logged_in(self, state=None):
        """Logged in is either needing to complete registration or done

        Args:
            state (str): logged in state [None: from cookie]
        Returns:
            bool: is in one of the logged in states
        """
        s = state or self._qcall_bound_state()
        return s in (_STATE_COMPLETE_REGISTRATION, _STATE_LOGGED_IN)

    def is_premium_user(self):
        return sirepo.auth_db.UserRole.has_role(
            self.logged_in_user(),
            sirepo.auth_role.ROLE_PAYMENT_PLAN_PREMIUM,
        )

    def logged_in_user(self, check_path=True):
        """Get the logged in user

        Args:
            check_path (bool): call `simulation_db.user_path` [True]
        Returns:
            str: uid of authenticated user
        """
        if self._logged_in_user:
            return self._logged_in_user
        u = self._qcall_bound_user()
        if not self.is_logged_in():
            raise sirepo.util.SRException(
                LOGIN_ROUTE_NAME,
                None,
                "user not logged in uid={}",
                u,
            )
        assert u, "no user in cookie: state={} method={}".format(
            self._qcall_bound_state(),
            self._qcall_bound_method(),
        )
        if check_path:
            simulation_db.user_path(u, check=True)
        return u

    def logged_in_user_name(self):
        """Return user_name for logged in user"""
        return self.user_name(
            uid=self.logged_in_user(),
            method=self._qcall_bound_method(),
        )

    def logged_in_user_set(self, uid, method=METHOD_GUEST):
        """Ephemeral login"""
        self._logged_in_user = uid
        self._logged_in_method = method

    def login(
        self,
        method=None,
        uid=None,
        model=None,
        sim_type=None,
        display_name=None,
        is_mock=False,
        want_redirect=False,
    ):
        """Login the user

        Raises an exception if successful, except in the case of methods

        Args:
            method (module): method module (only if is_mock) [None]
            uid (str): user to login [None]
            model (auth_db.UserDbBase): user to login (overrides uid) [None]
            sim_type (str): app to redirect to [None]
            display_name (str): to save as the display_name [None]
            is_mock (bool): simulationed login for api_srUnit [False]
            want_redirect (bool): http redirect on success [False]
        """
        if method is None:
            assert is_mock, "only used by api_srUnit"
            method = METHOD_GUEST
        if isinstance(method, str):
            method = _METHOD_MODULES[method]
        self._validate_method(method, sim_type=sim_type)
        guest_uid = None
        if model:
            uid = model.uid
            # if previously cookied as a guest, move the non-example simulations into uid below
            m = self._qcall_bound_method()
            if m == METHOD_GUEST and method.AUTH_METHOD != METHOD_GUEST:
                guest_uid = self._qcall_bound_user() if self.is_logged_in() else None
        if uid:
            self._login_user(method, uid)
        if method.AUTH_METHOD in _cfg.deprecated_methods:
            pkdlog("deprecated auth method={} uid={}".format(method.AUTH_METHOD, uid))
            if not uid:
                # No user so clear cookie so this method is removed
                self.reset_state()
            # We are logged in with a deprecated method, and now the user
            # needs to login with an allowed method.
            self.login_fail_redirect(
                sim_type=sim_type, module=method, reason="deprecated", reload_js=not uid
            )
        if not uid:
            # No user in the cookie and method didn't provide one so
            # the user might be switching methods (e.g. github to email or guest to email).
            # Not allowed to go to guest from other methods, because there's
            # no authentication for guest.
            # Or, this is just a new user, and we'll create one.
            uid = self._qcall_bound_user() if self.is_logged_in() else None
            m = self._qcall_bound_method()
            if uid and method.AUTH_METHOD not in (m, METHOD_GUEST):
                # switch this method to this uid (even for methods)
                # except if the same method, then assuming logging in as different user.
                # This handles the case where logging in as guest, creates a user every time
                self._login_user(method, uid)
            else:
                uid = self.create_user(lambda u: self._login_user(method, u), method)
            if model:
                model.uid = uid
                model.save()
        if display_name:
            self.complete_registration(self.parse_display_name(display_name))
        if is_mock:
            return
        if sim_type:
            if guest_uid and guest_uid != uid:
                simulation_db.migrate_guest_to_persistent_user(guest_uid, uid)
            self.login_success_response(sim_type, want_redirect)
        assert not method.AUTH_METHOD_VISIBLE

    def login_fail_redirect(
        self, sim_type=None, module=None, reason=None, reload_js=False
    ):
        raise sirepo.util.SRException(
            "loginFail",
            PKDict(
                method=module.AUTH_METHOD,
                reason=reason,
                reload_js=reload_js,
                sim_type=sim_type,
            ),
            "login failed: reason={} method={}",
            reason,
            module.AUTH_METHOD,
        )

    def login_success_response(self, sim_type, want_redirect=False):
        r = None
        if (
            self.qcall.cookie.get_value(_COOKIE_STATE) == _STATE_COMPLETE_REGISTRATION
            and self.qcall.cookie.get_value(_COOKIE_METHOD) == METHOD_GUEST
        ):
            self.complete_registration()
        if want_redirect:
            r = (
                "completeRegistration"
                if (
                    self.qcall.cookie.get_value(_COOKIE_STATE)
                    == _STATE_COMPLETE_REGISTRATION
                )
                else None
            )
            raise sirepo.util.Redirect(sirepo.uri.local_route(sim_type, route_name=r))
        raise sirepo.util.Response(
            response=self.qcall.reply_ok(PKDict(authState=self._auth_state())),
        )

    def need_complete_registration(self, model):
        """Does unauthenticated user need to complete registration?

        If the current method is deprecated, then we will end up asking
        the user for a name again, but that's ok.

        Does not work for guest (which don't have their own models anyway).

        Args:
            model (auth_db.UserDbBase): unauthenticated user record
        Returns:
            bool: True if user will be redirected to needCompleteRegistration
        """
        if not model.uid:
            return True
        return not sirepo.auth_db.UserRegistration.search_by(uid=model.uid).display_name

    def only_for_api_auth_state(self):
        return self._auth_state()

    def only_for_api_logout(self):
        sirepo.events.emit(
            self.qcall,
            "auth_logout",
            PKDict(uid=self._qcall_bound_user()),
        )
        self.qcall.cookie.set_value(_COOKIE_STATE, _STATE_LOGGED_OUT)
        self._set_log_user()

    def parse_display_name(self, value):
        res = value.strip()
        assert res, "invalid post data: displayName={}".format(value)
        return res

    def require_adm(self):
        u = self.require_user()
        if not sirepo.auth_db.UserRole.has_role(u, sirepo.auth_role.ROLE_ADM):
            sirepo.util.raise_forbidden(f"uid={u} role=ROLE_ADM not found")

    def require_auth_basic(self):
        m = _METHOD_MODULES["basic"]
        self._validate_method(m)
        uid = m.require_user(self.qcall)
        if not uid:
            raise sirepo.util.WWWAuthenticate()
        self.qcall.cookie.set_sentinel()
        self.login(m, uid=uid)

    def require_email_user(self):
        i = self.require_user()
        m = self._qcall_bound_method()
        if m != METHOD_EMAIL:
            sirepo.util.raise_forbidden(f"method={m} is not email for uid={i}")

    def require_user(self):
        """Asserts whether user is logged in

        Returns:
            str: user id
        """
        e = None
        m = self._qcall_bound_method()
        p = None
        r = LOGIN_ROUTE_NAME
        s = self._qcall_bound_state()
        u = self._qcall_bound_user()
        if s is None:
            pass
        elif s == _STATE_LOGGED_IN:
            if m in _cfg.methods:

                f = getattr(_METHOD_MODULES[m], "validate_login", None)
                if f:
                    pkdc("validate_login method={}", m)
                    f(self.qcall)
                return u
            if m in _cfg.deprecated_methods:
                e = "deprecated"
            else:
                e = "invalid"
                self.reset_state()
                p = PKDict(reload_js=True)
            e = "auth_method={} is {}, forcing login: uid=".format(m, e, u)
        elif s == _STATE_LOGGED_OUT:
            e = "logged out uid={}".format(u)
            if m in _cfg.deprecated_methods:
                # Force login to this specific method so we can migrate to valid method
                r = "loginWith"
                p = PKDict({":method": m})
                e = "forced {}={} uid={}".format(m, r, p)
        elif s == _STATE_COMPLETE_REGISTRATION:
            if m == METHOD_GUEST:
                pkdc("guest completeRegistration={}", u)
                self.complete_registration()
                return u
            r = "completeRegistration"
            e = "uid={} needs to complete registration".format(u)
        else:
            self.qcall.cookie.reset_state(
                "uid={} state={} invalid, cannot continue".format(s, u)
            )
            p = PKDict(reload_js=True)
            e = "invalid cookie state={} uid={}".format(s, u)
        pkdc("SRException uid={} route={} params={} method={} error={}", u, r, p, m, e)
        raise sirepo.util.SRException(
            r, p, *(("user not logged in: {}", e) if e else ())
        )

    def reset_state(self):
        self.qcall.cookie.unchecked_remove(_COOKIE_USER)
        self.qcall.cookie.unchecked_remove(_COOKIE_METHOD)
        self.qcall.cookie.set_value(_COOKIE_STATE, _STATE_LOGGED_OUT)
        self._set_log_user()

    def unchecked_get_user(self, uid):
        with sirepo.util.THREAD_LOCK:
            u = sirepo.auth_db.UserRegistration.search_by(uid=uid)
            if u:
                return u.uid
            return None

    def user_dir_not_found(self, user_dir, uid):
        """Called by http_reply when user_dir is not found

        Deletes any user records and resets auth state.

        Args:
            user_dir (str): directory not found
            uid (str): user
        """
        with sirepo.util.THREAD_LOCK:
            for m in _METHOD_MODULES.values():
                u = self._method_user_model(m, uid)
                if u:
                    u.delete()
            u = sirepo.auth_db.UserRegistration.search_by(uid=uid)
            if u:
                u.delete()
        self.reset_state()
        pkdlog("user_dir={} uid={}", user_dir, uid)
        return self.qcall.reply_redirect_for_app_root()

    def user_display_name(self, uid):
        return sirepo.auth_db.UserRegistration.search_by(uid=uid).display_name

    def user_if_logged_in(self, method):
        """Verify user is logged in and method matches

        Args:
            method (str): method must be logged in as
        """
        if not self.is_logged_in():
            return None
        m = self._qcall_bound_method()
        if m != method:
            return None
        return self._qcall_bound_user()

    def user_name(self, uid, method):
        """Return user_name"""
        u = getattr(_METHOD_MODULES[method], "UserModel", None)
        if u:
            with sirepo.util.THREAD_LOCK:
                return u.search_by(uid=uid).user_name
        elif method == METHOD_GUEST:
            return f"{METHOD_GUEST}-{uid}"
        raise AssertionError(f"user_name not found for uid={uid} with method={method}")

    def user_registration(self, uid, display_name=None):
        """Get UserRegistration record or create one

        Args:
            uid (str): registrant
            display_name (str): display_name of user
        Returns:
            auth.UserRegistration: record (potentially blank)
        """
        res = sirepo.auth_db.UserRegistration.search_by(uid=uid)
        if not res:
            res = sirepo.auth_db.UserRegistration(
                created=datetime.datetime.utcnow(),
                display_name=display_name,
                uid=uid,
            )
            res.save()
        return res

    def _auth_state(self):
        def _get_slack_uri():
            return sirepo.feature_config.cfg().slack_uri + (
                self._qcall_bound_user() or ""
            )

        s = self._qcall_bound_state()
        v = pkcollections.Dict(
            avatarUrl=None,
            displayName=None,
            guestIsOnlyMethod=not non_guest_methods,
            isGuestUser=False,
            isLoggedIn=self.is_logged_in(s),
            isLoginExpired=False,
            jobRunModeMap=simulation_db.JOB_RUN_MODE_MAP,
            method=self._qcall_bound_method(),
            needCompleteRegistration=s == _STATE_COMPLETE_REGISTRATION,
            roles=[],
            slackUri=_get_slack_uri(),
            userName=None,
            visibleMethods=visible_methods,
        )
        if "sbatch" in v.jobRunModeMap:
            v.sbatchQueueMaxes = job.NERSC_QUEUE_MAX
        u = self._qcall_bound_user()
        if v.isLoggedIn:
            if v.method == METHOD_GUEST:
                # currently only method to expire login
                v.displayName = _GUEST_USER_DISPLAY_NAME
                v.isGuestUser = True
                v.isLoginExpired = _METHOD_MODULES[METHOD_GUEST].is_login_expired(
                    self.qcall
                )
                v.needCompleteRegistration = False
                v.visibleMethods = non_guest_methods
            else:
                r = sirepo.auth_db.UserRegistration.search_by(uid=u)
                if r:
                    v.displayName = r.display_name
            v.roles = sirepo.auth_db.UserRole.get_roles(u)
            self._plan(v)
            self._method_auth_state(v, u)
        if pkconfig.channel_in_internal_test():
            # useful for testing/debugging
            v.uid = u
        pkdc("state={}", v)
        return v

    def _create_roles_for_new_user(self, uid, method):
        r = sirepo.auth_role.for_new_user(method == METHOD_GUEST)
        if r:
            sirepo.auth_db.UserRole.add_roles(uid, r)

    def _login_user(self, module, uid):
        """Set up the cookie for logged in state

        If a deprecated or non-visible method, just login. Otherwise, check the db
        for registration.

        Args:
            module (module): what auth method
            uid (str): which uid

        """
        self.qcall.cookie.set_value(_COOKIE_USER, uid)
        self.qcall.cookie.set_value(_COOKIE_METHOD, module.AUTH_METHOD)
        s = _STATE_LOGGED_IN
        if module.AUTH_METHOD_VISIBLE and module.AUTH_METHOD in _cfg.methods:
            u = self.user_registration(uid)
            if not u.display_name:
                s = _STATE_COMPLETE_REGISTRATION
        self.qcall.cookie.set_value(_COOKIE_STATE, s)
        self._set_log_user()

    def _method_auth_state(self, values, uid):
        if values.method not in _METHOD_MODULES:
            pkdlog(
                'auth state method: "{}" not present in supported methods: {}',
                values.method,
                _METHOD_MODULES.keys(),
            )
            return
        m = _METHOD_MODULES[values.method]
        u = self._method_user_model(m, uid)
        if not u:
            return
        values.userName = u.user_name
        if hasattr(m, "avatar_uri"):
            values.avatarUrl = m.avatar_uri(self.qcall, u, _AVATAR_SIZE)

    def _method_user_model(self, module, uid):
        if not hasattr(module, "UserModel"):
            return None
        return module.UserModel.search_by(uid=uid)

    def _plan(self, data):
        r = data.roles
        if sirepo.auth_role.ROLE_PAYMENT_PLAN_ENTERPRISE in r:
            data.paymentPlan = _PAYMENT_PLAN_ENTERPRISE
            data.upgradeToPlan = None
        elif sirepo.auth_role.ROLE_PAYMENT_PLAN_PREMIUM in r:
            data.paymentPlan = _PAYMENT_PLAN_PREMIUM
            data.upgradeToPlan = _PAYMENT_PLAN_ENTERPRISE
        else:
            data.paymentPlan = _PAYMENT_PLAN_BASIC
            data.upgradeToPlan = _PAYMENT_PLAN_PREMIUM

    def _qcall_bound_method(self):
        return self._logged_in_method or self.qcall.cookie.unchecked_get_value(
            _COOKIE_METHOD
        )

    def _qcall_bound_state(self):
        if self._logged_in_user:
            return _STATE_LOGGED_IN
        return self.qcall.cookie.unchecked_get_value(_COOKIE_STATE)

    def _qcall_bound_user(self):
        return _cfg.logged_in_user or self.qcall.cookie.unchecked_get_value(
            _COOKIE_USER
        )

    def _set_log_user(self):
        def _user():
            u = self._qcall_bound_user()
            if not u:
                return "="
            return self._qcall_bound_state() + "-" + u

        sirepo.flask.set_log_user(_user)

    def _validate_method(self, module, sim_type=None):
        if module.AUTH_METHOD in valid_methods:
            return None
        pkdlog("invalid auth method={}".format(module.AUTH_METHOD))
        self.login_fail_redirect(sim_type, module, "invalid-method", reload_js=True)
