"""Authentication

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkcollections
from pykern import pkconfig
from pykern import pkinspect
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp, pkdexc
import contextlib
import datetime
import importlib
import sirepo.auth_db
import sirepo.auth_role
import sirepo.cookie
import sirepo.events
import sirepo.feature_config
import sirepo.job
import sirepo.payments
import sirepo.quest
import sirepo.reply
import sirepo.request
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
_PAYMENT_PLAN_PREMIUM = sirepo.auth_role.ROLE_PLAN_PREMIUM
_ALL_PAYMENT_PLANS = (
    _PAYMENT_PLAN_BASIC,
    _PAYMENT_PLAN_PREMIUM,
)

_STATE_LOGGED_IN = "li"
_STATE_LOGGED_OUT = "lo"
_STATE_COMPLETE_REGISTRATION = "cr"

#: name to module object
_METHOD_MODULES = PKDict()

# TODO(robnagler) probably from the schema
#: For formatting the size parameter to an avatar_uri
_AVATAR_SIZE = 40

#: methods + deprecated_methods
valid_methods = None

#: Methods that the user is allowed to see
visible_methods = None

#: visible_methods excluding guest
non_guest_methods = None

#: in auth state
_cookie_http_name = None

_cfg = None


def init_quest(qcall, internal_req=None):
    """Under development

    Args:
        qcall (quest.API): context for APIs and CLIs
        internal_req (object): context of web framework, pkcli, unit test, etc.
    """
    o = _Auth(qcall)
    sirepo.auth_db.init_quest(qcall)
    if (
        not _cfg.logged_in_user
        and internal_req
        or qcall.bucket_unchecked_get("in_pkcli")
    ):
        sirepo.request.init_quest(qcall, internal_req=internal_req)
        sirepo.reply.init_quest(qcall)
        # TODO(robnagler): process auth basic header, too. this
        # should not cookie but route to auth_basic.
        sirepo.cookie.init_quest(qcall)
        # TODO(robnagler) auth_db
        o._set_log_user()


def init_module(**imports):
    global _cfg

    def _init_full():
        global visible_methods, valid_methods, non_guest_methods, _cookie_http_name

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
        if sorted(s) != sorted(_ALL_PAYMENT_PLANS):
            raise AssertionError(
                f"payment plans from SCHEMA_COMMON={s} not equal to _ALL_PAYMENT_PLANS={_ALL_PAYMENT_PLANS}",
            )
        _cookie_http_name = sirepo.cookie.unchecked_http_name()

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

    # Keys passed to child quests (nested call_api) so login state is cascaded
    _INIT_QUEST_FOR_CHILD_KEYS = frozenset(
        (
            "_logged_in_user",
            "_logged_in_method",
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logged_in_user = _cfg.logged_in_user
        self._logged_in_method = METHOD_GUEST if _cfg.logged_in_user else None

    def check_sim_type_role(self, sim_type, force_sim_type_required_for_api=False):
        from sirepo import auth_role_moderation, oauth, uri_router

        t = sirepo.template.assert_sim_type(sim_type)
        self.qcall.sim_type_set(t)
        if t not in sirepo.feature_config.auth_controlled_sim_types():
            return
        if (
            not force_sim_type_required_for_api
            and not uri_router.maybe_sim_type_required_for_api(self.qcall)
        ):
            return
        u = self.logged_in_user()
        r = sirepo.auth_role.for_sim_type(t)
        if self.qcall.auth_db.model("UserRole").has_active_role(role=r, uid=u):
            return
        if r in sirepo.auth_role.for_proprietary_oauth_sim_types():
            oauth.raise_authorize_redirect(self.qcall, sirepo.auth_role.sim_type(r))
        if r in sirepo.auth_role.for_moderated_sim_types():
            auth_role_moderation.raise_control_for_user(self.qcall, u, r)
        raise sirepo.util.Forbidden(f"uid={u} does not have access to sim_type={t}")

    def _assert_role_user(self):
        u = self.logged_in_user()
        if not self.qcall.auth_db.model("UserRole").has_active_role(
            role=sirepo.auth_role.ROLE_USER,
            uid=u,
        ):
            raise sirepo.util.Forbidden(
                f"uid={u} role={sirepo.auth_role.ROLE_USER} not found"
            )
        return u

    def complete_registration(self, name=None):
        """Update the database with the user's display_name and sets state to logged-in.
        Guests will have no name.
        """
        if self._qcall_bound_method() == METHOD_GUEST and name is not None:
            raise AssertionError(
                "user name={name} should be None with method={METHOD_GUEST}",
            )
        self.user_registration(self._qcall_bound_user(), display_name=name)
        self.qcall.cookie.set_value(_COOKIE_STATE, _STATE_LOGGED_IN)

    def cookie_cleaner(self, values):
        """Migrate from old cookie values

        Always sets _COOKIE_STATE, which is our sentinel.

        Args:
            values (PKDict): just parsed values
        Returns:
            PKDict, bool: (unmodified or migrated values, True if modified)
        """
        if values.get(_COOKIE_STATE):
            # normal case: this module has seen a cookie at least once
            # check for _cfg.methods changes; invalid methods cause a logout.
            # No method is fine, because not logged in.
            m = values.get(_COOKIE_METHOD)
            if not m or m in valid_methods:
                return values, False
            # invalid method (changed config), reset state
            pkdlog(
                "possibly misconfigured server: invalid cookie_method={}, clearing auth values={}",
                m,
                values,
            )
            pkcollections.unchecked_del(
                values, _COOKIE_METHOD, _COOKIE_USER, _COOKIE_STATE
            )
            return values, True
        # data cleaning; do not need old auth values
        if values.get("sru") or values.get("uid"):
            pkdlog(
                "unknown cookie values, clearing completely, not migrating: {}", values
            )
            return PKDict(), True
        # normal case: new visitor (no user or state); set logged out
        values[_COOKIE_STATE] = _STATE_LOGGED_OUT
        return values, True

    def create_user_from_email(self, email, display_name):
        u = self._create_user(_METHOD_MODULES[METHOD_EMAIL], want_login=False)
        self.user_registration(uid=u, display_name=display_name)
        self.qcall.auth_db.model(
            self.get_module(METHOD_EMAIL).UserModel,
            unverified_email=email,
            uid=u,
            user_name=email,
        ).save()
        return u

    def get_module(self, name):
        return _METHOD_MODULES[name]

    def guest_uids(self):
        """All of the uids corresponding to guest users."""
        return self.qcall.auth_db.model("UserRegistration").search_all_for_column(
            "uid", display_name=None
        )

    def is_logged_in(self, state=None):
        """Logged in is either needing to complete registration or done

        Does not check simulation dir

        Args:
            state (str): logged in state [None: from cookie]
        Returns:
            bool: is in one of the logged in states
        """
        s = state or self._qcall_bound_state()
        return s in (_STATE_COMPLETE_REGISTRATION, _STATE_LOGGED_IN)

    def is_premium_user(self):
        return self.qcall.auth_db.model("UserRole").has_active_role(
            role=sirepo.auth_role.ROLE_PLAN_PREMIUM,
            uid=self.logged_in_user(),
        )

    def logged_in_user(self, check_path=True):
        """Get the logged in user

        Args:
            check_path (bool): call `simulation_db.user_path` [True]
        Returns:
            str: uid of authenticated user
        """
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
            simulation_db.user_path(uid=u, check=True)
        return u

    def logged_in_user_name(self):
        """Return user_name for logged in user"""
        return self.user_name(
            uid=self.logged_in_user(),
            method=self._qcall_bound_method(),
        )

    def logged_in_user_name_local_part(self):
        """If user_name is email address, return the local part.
        Otherwise, just return user_name.
        """

        return self.logged_in_user_name().split("@")[0].lower()

    @contextlib.contextmanager
    def logged_in_user_set(self, uid, method=METHOD_GUEST):
        """Ephemeral login or may be used to logout"""
        u = self._logged_in_user
        m = self._logged_in_method
        try:
            self._logged_in_user = uid
            self._logged_in_method = None if uid is None else method
            yield
        finally:
            self._logged_in_user = u
            self._logged_in_method = m

    def login(
        self,
        method=None,
        uid=None,
        model=None,
        sim_type=None,
        display_name=None,
        want_redirect=False,
        moderation_reason=None,
    ):
        """Login the user

        Raises an exception if successful, except in the case of methods

        Args:
            method (module or str): method module
            uid (str): user to login [None]
            model (auth_db.UserDbBase): user to login (overrides uid) [None]
            sim_type (str): app to redirect to [None]
            display_name (str): to save as the display_name [None]
            want_redirect (bool): http redirect on success [False]
        """
        from sirepo import auth_role_moderation

        mm = _METHOD_MODULES[method] if isinstance(method, str) else method
        self._validate_method(mm)
        guest_uid = None
        if model:
            uid = model.uid
            # if previously cookied as a guest, move the non-example simulations into uid below
            m = self._qcall_bound_method()
            if m == METHOD_GUEST and mm.AUTH_METHOD != METHOD_GUEST:
                guest_uid = self._qcall_bound_user() if self.is_logged_in() else None
        if uid:
            self._login_user(mm, uid)
        if mm.AUTH_METHOD in _cfg.deprecated_methods:
            pkdlog("deprecated auth method={} uid={}".format(mm.AUTH_METHOD, uid))
            if not uid:
                # No user so clear cookie so this method is removed
                self.reset_state()
            # We are logged in with a deprecated method, and now the user
            # needs to login with an allowed method.
            self.login_fail_redirect(module=mm, reason="deprecated")
        if not uid:
            # No user in the cookie and method didn't provide one so
            # the user might be switching methods (e.g. guest to email).
            # Not allowed to go to guest from other methods, because there's
            # no authentication for guest.
            # Or, this is just a new user, and we'll create one.
            uid = self._qcall_bound_user() if self.is_logged_in() else None
            m = self._qcall_bound_method()
            if uid and mm.AUTH_METHOD not in (m, METHOD_GUEST):
                # switch this method to this uid (even for methods)
                # except if the same method, then assuming logging in as different user.
                # This handles the case where logging in as guest, creates a user every time
                self._login_user(mm, uid)
            else:
                uid = self._create_user(mm, want_login=True)
            if model:
                model.uid = uid
                model.save()
        # see if the user has completed registration already (must be done before setting display_name)
        nr = self.need_complete_registration(uid)
        if display_name:
            self.complete_registration(self.parse_display_name(display_name))
        if nr and sirepo.feature_config.cfg().is_registration_moderated:
            auth_role_moderation.save_moderation_reason(
                self.qcall,
                uid,
                sim_type,
                moderation_reason,
            )
        if sim_type:
            if guest_uid and guest_uid != uid:
                self.qcall.auth_db.commit()
                simulation_db.migrate_guest_to_persistent_user(
                    guest_uid,
                    uid,
                    qcall=self.qcall,
                )
            self.login_success_response(sim_type, want_redirect)
        assert not mm.AUTH_METHOD_VISIBLE

    def login_fail_redirect(self, module=None, reason=None):
        raise sirepo.util.SRException(
            "loginFail",
            PKDict(method=module.AUTH_METHOD, reason=reason),
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
        raise sirepo.util.SReplyExc(
            sreply=self.qcall.reply_ok(PKDict(authState=self._auth_state())),
        )

    def need_complete_registration(self, model_or_uid):
        """Does unauthenticated user need to complete registration?

        If the current method is deprecated, then we will end up asking
        the user for a name again, but that's ok.

        Does not work for guest (which don't have their own models anyway).

        Args:
            model_or_uid (object): unauthenticated user record or uid
        Returns:
            bool: True if user will be redirected to needCompleteRegistration
        """
        u = model_or_uid if isinstance(model_or_uid, str) else model_or_uid.uid
        if not u:
            return True
        return not self.user_display_name(uid=u)

    def only_for_api_auth_state(self):
        try:
            try:
                return self._auth_state()
            except sirepo.util.UserDirNotFound as e:
                # Clear login and return new auth_state
                self._handle_user_dir_not_found(**e.sr_args)
                return self._auth_state()
        except Exception as e:
            pkdlog("exception={} stack={}", e, pkdexc())
            # POSIT: minimal authState record, see _auth_state
            return PKDict(
                displayName=None,
                guestIsOnlyMethod=not non_guest_methods,
                isGuestUser=False,
                isLoggedIn=False,
                isModerated=sirepo.feature_config.cfg().is_registration_moderated,
                roles=PKDict(),
                userName=None,
                uiWebSocket=sirepo.feature_config.cfg().ui_websocket,
                visibleMethods=visible_methods,
            )

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
        if not self.qcall.auth_db.model("UserRole").has_active_role(
            role=sirepo.auth_role.ROLE_ADM,
            uid=u,
        ):
            raise sirepo.util.Forbidden(
                f"uid={u} role={sirepo.auth_role.ROLE_ADM} not found"
            )

    def require_auth_basic(self):
        m = _METHOD_MODULES["basic"]
        self._validate_method(m)
        uid = m.require_user(self.qcall)
        if not uid:
            raise sirepo.util.WWWAuthenticate()
        self.qcall.cookie.set_sentinel()
        self._login_user(m, uid)

    def require_email_user(self):
        i = self.require_user()
        m = self._qcall_bound_method()
        if m != METHOD_EMAIL:
            raise sirepo.util.Forbidden(f"method={m} is not email for uid={i}")

    def require_plan(self):
        u = self.require_user()
        if not self.qcall.auth_db.model("UserRole").has_active_plan(uid=u):
            raise sirepo.util.PlanExpired(f"uid={u} has no active plans")

    def require_premium(self):
        if not self.is_premium_user():
            raise sirepo.util.Forbidden("not premium user")

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
        if u:
            # Will raise an exception if dir not found
            simulation_db.user_path(uid=u, check=True)
        if s is None:
            pass
        elif s == _STATE_LOGGED_IN:
            if m in _cfg.methods:
                return self._assert_role_user()
            if m in _cfg.deprecated_methods:
                e = "deprecated"
            else:
                e = "invalid"
                self.reset_state()
                p = PKDict(reload_js=True)
            e = f"auth_method={m} is {e}, forcing login: uid={u}"
        elif s == _STATE_LOGGED_OUT:
            e = "logged out uid={}".format(u)
            if m in _cfg.deprecated_methods:
                # Force login to this specific method so we can migrate to valid method
                r = "loginWith"
                p = PKDict({":method": m})
                e = f"forced {r}={m} uid={u}"
        elif s == _STATE_COMPLETE_REGISTRATION:
            if m == METHOD_GUEST:
                pkdc("guest completeRegistration={}", u)
                self.complete_registration()
                self.qcall.auth_db.commit()
                return self._assert_role_user()
            r = "completeRegistration"
            e = "uid={} needs to complete registration".format(u)
        else:
            self.qcall.cookie.reset_state(f"state={s} uid={u} invalid, cannot continue")
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

    @contextlib.contextmanager
    def srunit_user(self, want_global):
        """Create a new guest user and log them in

        **Only called from srunit**
        """
        from pykern import pkunit

        if not pkunit.is_test_run():
            raise AssertionError("must be in pkunit test run")
        rv = self._create_user(_METHOD_MODULES[METHOD_GUEST], want_login=True)
        p = None
        try:
            if want_global:
                p = _cfg.logged_in_user
                _cfg.logged_in_user = rv
                simulation_db.srunit_logged_in_user(rv)
            yield rv
        finally:
            if want_global:
                _cfg.logged_in_user = p
                simulation_db.srunit_logged_in_user(p)

    def unchecked_get_user(self, uid_or_user_name):
        # support other user_name types
        # POSIT: Uid's are from the base62 charset so an '@' implies an email.
        if "@" in uid_or_user_name:
            a = PKDict(user_name=uid_or_user_name)
            m = self.qcall.auth_db.model(_METHOD_MODULES[METHOD_EMAIL].UserModel)
        else:
            a = PKDict(uid=simulation_db.assert_uid(uid_or_user_name))
            m = self.qcall.auth_db.model("UserRegistration")
        if u := m.unchecked_search_by(**a):
            return u.uid
        return None

    def user_dir_not_found(self, user_dir, uid):
        """Called by sirepo.reply when user_dir is not found

        Deletes any user records and resets auth state.

        Args:
            user_dir (str): directory not found
            uid (str): user
        """
        self._handle_user_dir_not_found(user_dir, uid)
        return self.qcall.reply_redirect_for_app_root()

    def user_display_name(self, uid):
        return (
            self.qcall.auth_db.model("UserRegistration").search_by(uid=uid).display_name
        )

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

    def user_name(self, uid, method=None):
        """Return user_name"""
        m = method or self._qcall_bound_method()
        t = getattr(_METHOD_MODULES[m], "UserModel", None)
        if t:
            return self.qcall.auth_db.model(t).search_by(uid=uid).user_name
        elif m == METHOD_GUEST:
            return f"{METHOD_GUEST}-{uid}"
        raise AssertionError(f"user_name not found for uid={uid} with method={m}")

    def user_registration(self, uid, display_name=None):
        """Get UserRegistration record or create one

        Args:
            uid (str): registrant
            display_name (str): display_name of user
        Returns:
            auth.UserRegistration: record (potentially blank)
        """
        res = self.qcall.auth_db.model("UserRegistration").unchecked_search_by(uid=uid)
        if res:
            if display_name is not None:
                res.display_name = display_name
                res.save()
        else:
            res = self.qcall.auth_db.model(
                "UserRegistration",
                created=datetime.datetime.utcnow(),
                display_name=display_name,
                uid=uid,
            )
            res.save()
        return res

    def _auth_state(self):
        s = self._qcall_bound_state()
        v = PKDict(
            avatarUrl=None,
            cookieName=_cookie_http_name,
            displayName=None,
            guestIsOnlyMethod=not non_guest_methods,
            isGuestUser=False,
            isLoggedIn=self.is_logged_in(s),
            isModerated=sirepo.feature_config.cfg().is_registration_moderated,
            jobRunModeMap=simulation_db.JOB_RUN_MODE_MAP,
            max_message_bytes=sirepo.job.cfg().max_message_bytes,
            method=self._qcall_bound_method(),
            needCompleteRegistration=s == _STATE_COMPLETE_REGISTRATION,
            roles=[],
            userName=None,
            uiWebSocket=sirepo.feature_config.cfg().ui_websocket,
            visibleMethods=visible_methods,
        )
        if "sbatch" in v.jobRunModeMap:
            v.sbatchQueueMaxes = sirepo.job.NERSC_QUEUE_MAX
        if sirepo.feature_config.have_payments():
            v.stripePublishableKey = sirepo.payments.cfg().stripe_publishable_key
        u = self._qcall_bound_user()
        if v.isLoggedIn:
            if v.method == METHOD_GUEST:
                v.displayName = _GUEST_USER_DISPLAY_NAME
                v.isGuestUser = True
                v.needCompleteRegistration = False
                v.visibleMethods = non_guest_methods
            else:
                r = self.qcall.auth_db.model("UserRegistration").unchecked_search_by(
                    uid=u
                )
                if r:
                    v.displayName = r.display_name
            v.roles = {
                x.role: (x.expiration.timestamp() if x.expiration else None)
                for x in self.qcall.auth_db.model("UserRole").get_roles_and_expiration(
                    u
                )
            }
            self._plan(v)
            self._method_auth_state(v, u)
        if pkconfig.channel_in_internal_test():
            # useful for testing/debugging
            v.uid = u
        pkdc("state={}", v)
        return v

    def _create_user(self, module, want_login):
        u = simulation_db.user_create()
        if want_login:
            self._login_user(module, u)
        self.qcall.auth_db.model("UserRole").add_roles(
            roles=sirepo.auth_role.for_new_user(module.AUTH_METHOD),
            uid=u,
        )
        return u

    def _handle_user_dir_not_found(self, user_dir, uid):
        for m in _METHOD_MODULES.values():
            u = self._method_user_model(m, uid)
            if u:
                u.delete()
        u = self.qcall.auth_db.model("UserRegistration").unchecked_search_by(uid=uid)
        if u:
            u.delete()
        self.reset_state()
        self.qcall.auth_db.commit()
        pkdlog("user_dir={} uid={}", user_dir, uid)

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
        return self.qcall.auth_db.model(module.UserModel).unchecked_search_by(uid=uid)

    def _plan(self, data):
        r = data.roles
        if sirepo.auth_role.ROLE_PLAN_PREMIUM in r:
            data.paymentPlan = _PAYMENT_PLAN_PREMIUM
            data.upgradeToPlan = None
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
        return self._logged_in_user or self.qcall.cookie.unchecked_get_value(
            _COOKIE_USER
        )

    def _set_log_user(self):
        def _user():
            u = self._qcall_bound_user()
            if not u:
                return ""
            return self._qcall_bound_state() + "-" + u

        self.qcall.sreq.set_log_user(_user())

    def _validate_method(self, module):
        if module.AUTH_METHOD in valid_methods:
            return None
        pkdlog("invalid auth method={}".format(module.AUTH_METHOD))
        self.login_fail_redirect(module, "invalid-method")
