"""OpenID Connect authorization-code login with a single trusted provider.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from authlib.integrations.base_client.errors import OAuthError
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.oidc.core import CodeIDToken
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet
from pykern import pkconfig, pkinspect
from pykern.pkdebug import pkdlog
import datetime
import hmac
import httpx
import pyisemail
import secrets
import sirepo.feature_config
import sirepo.cron
import sirepo.quest
import sirepo.srtime
import sirepo.uri
import sirepo.util
import urllib.parse


AUTH_METHOD = "oidc"
AUTH_METHOD_VISIBLE = True
UserModel = "AuthEmailUser"
this_module = pkinspect.this_module()

_COOKIE_STATE = "oidc_state"
_COOKIE_REGISTRATION = "oidc_registration"
_LOGIN_LIFETIME = datetime.timedelta(minutes=10)
_cfg = None
_CLEANUP_CRON = None


class API(sirepo.quest.API):
    @sirepo.quest.Spec("allow_cookieless_set_user")
    async def api_authOidcLogin(self, simulation_type):
        try:
            return await self._login_redirect(simulation_type)
        except sirepo.util.Forbidden:
            self.auth.login_fail_redirect(this_module, "oauth-state")

    async def _login_redirect(self, simulation_type):
        _require_http_get(self)
        req = self.parse_params(type=simulation_type)
        if self.auth.user_if_logged_in(AUTH_METHOD):
            self.auth.login_success_response(req.type, want_redirect=True)
        async with _client() as client:
            metadata = await _metadata(client)
            state = secrets.token_urlsafe(32)
            nonce = secrets.token_urlsafe(32)
            verifier = secrets.token_urlsafe(48)
            url, _ = client.create_authorization_url(
                metadata["authorization_endpoint"],
                state=state,
                nonce=nonce,
                code_verifier=verifier,
                response_mode="query",
            )
        m = self.auth_db.model("AuthOidcLogin")
        m.query().filter(type(m).expires < sirepo.srtime.utc_now()).delete()
        if previous := self.cookie.unchecked_get_value(_COOKIE_STATE):
            if old := m.unchecked_search_by(state=previous):
                old.delete()
        if previous := self.cookie.unchecked_get_value(_COOKIE_REGISTRATION):
            if old := m.unchecked_search_by(state=previous):
                old.delete()
            self.cookie.unchecked_remove(_COOKIE_REGISTRATION)
        m.new(
            state=state,
            nonce=nonce,
            verifier=verifier,
            simulation_type=req.type,
            expires=sirepo.srtime.utc_now() + _LOGIN_LIFETIME,
        ).save()
        self.cookie.set_value(_COOKIE_STATE, state)
        return self.reply_redirect(url)

    @sirepo.quest.Spec("allow_cookieless_set_user")
    async def api_authOidcCallback(self):
        try:
            return await self._callback()
        except sirepo.util.Forbidden:
            self.auth.login_fail_redirect(this_module, "oauth-state")

    @sirepo.quest.Spec("require_cookie_sentinel", display_name="UserDisplayName")
    async def api_authOidcCompleteRegistration(self):
        req = self.parse_post()
        pending = self.auth_db.model("AuthOidcLogin").unchecked_search_by(
            state=self.cookie.unchecked_get_value(_COOKIE_REGISTRATION) or ""
        )
        if (
            not pending
            or not pending.email
            or pending.expires < sirepo.srtime.utc_now()
        ):
            self.auth.login_fail_redirect(this_module, "oauth-state")
        if pending.simulation_type != req.type:
            raise sirepo.util.BadRequest("OIDC registration application mismatch")
        moderated = sirepo.feature_config.cfg().is_registration_moderated
        reason = req.req_data.get("reason")
        if moderated and (not isinstance(reason, str) or not reason.strip()):
            raise sirepo.util.UserAlert("Reason for requesting access not provided")
        name = self.auth.parse_display_name(req.req_data.get("displayName"))
        email = pending.email
        if pending.query().filter_by(state=pending.state).delete() != 1:
            self.auth.login_fail_redirect(this_module, "oauth-state")
        self.cookie.unchecked_remove(_COOKIE_REGISTRATION)
        _login(
            self,
            dict(sub="registration", email=email, email_verified=True),
            req.type,
            display_name=name,
            moderation_reason=reason,
            want_redirect=False,
        )

    async def _callback(self):
        _require_http_get(self)
        params = urllib.parse.parse_qs(
            urllib.parse.urlsplit(self.sreq.http_request_uri).query,
            keep_blank_values=True,
        )
        if any(len(v) != 1 for v in params.values()):
            raise sirepo.util.Forbidden("duplicate OIDC callback parameters")
        params = {k: v[0] for k, v in params.items()}
        state = params.get("state", "")
        expected = self.cookie.unchecked_get_value(_COOKIE_STATE)
        if not expected or not hmac.compare_digest(
            state.encode("utf-8"), expected.encode("utf-8")
        ):
            raise sirepo.util.Forbidden("invalid OIDC login state")
        pending = self.auth_db.model("AuthOidcLogin").unchecked_search_by(state=state)
        self.cookie.unchecked_remove(_COOKIE_STATE)
        if not pending or pending.email or pending.expires < sirepo.srtime.utc_now():
            raise sirepo.util.Forbidden("expired or consumed OIDC login state")
        login = pending.as_pkdict()
        consumed = pending.query().filter_by(state=state).delete()
        # Consume the request before network I/O, including failed exchanges.
        self.auth_db.commit()
        if consumed != 1:
            raise sirepo.util.Forbidden("consumed OIDC login state")
        if params.get("error"):
            raise sirepo.util.Forbidden("OIDC authorization was denied")
        if not params.get("code"):
            raise sirepo.util.Forbidden("missing OIDC authorization code")
        if params.get("iss", _cfg.issuer) != _cfg.issuer:
            raise sirepo.util.Forbidden("invalid OIDC authorization issuer")
        try:
            async with _client() as client:
                metadata = await _metadata(client)
                token = await client.fetch_token(
                    metadata["token_endpoint"],
                    grant_type="authorization_code",
                    code=params["code"],
                    code_verifier=login.verifier,
                )
                if not token.get("id_token"):
                    raise sirepo.util.Forbidden("missing OIDC ID token")
                response = await client.request(
                    "GET", metadata["jwks_uri"], withhold_token=True
                )
                response.raise_for_status()
                decoded = jwt.decode(
                    token["id_token"],
                    KeySet.import_key_set(response.json()),
                    algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
                )
                claims = CodeIDToken(
                    decoded.claims,
                    decoded.header,
                    options={
                        "iss": {"essential": True, "value": _cfg.issuer},
                        "aud": {"essential": True, "value": _cfg.client_id},
                    },
                    params={
                        "nonce": login.nonce,
                        "client_id": _cfg.client_id,
                        "access_token": token.get("access_token"),
                    },
                )
                claims.validate(leeway=30)
        except (
            OAuthError,
            JoseError,
            httpx.HTTPError,
            ValueError,
            KeyError,
            TypeError,
        ) as e:
            pkdlog("OIDC token exchange or validation failed: {}", type(e).__name__)
            raise sirepo.util.Forbidden("OIDC authentication failed") from None
        _registration_or_login(self, claims, login.simulation_type)


def init_apis(*args, **kwargs):
    global _cfg, _CLEANUP_CRON

    _cfg = pkconfig.init(
        issuer=pkconfig.Required(_cfg_url, "Exact OIDC provider issuer URL"),
        client_id=pkconfig.Required(str, "OIDC client identifier"),
        client_secret=pkconfig.Required(str, "OIDC confidential client secret"),
        redirect_uri=pkconfig.Required(
            _cfg_url, "Registered public URL ending in /auth-oidc-callback"
        ),
        token_endpoint_auth_method=(
            "client_secret_basic",
            str,
            "Token authentication: client_secret_basic or client_secret_post",
        ),
    )
    if _cfg.token_endpoint_auth_method not in (
        "client_secret_basic",
        "client_secret_post",
    ):
        raise AssertionError("invalid OIDC token_endpoint_auth_method")
    if urllib.parse.urlsplit(_cfg.issuer).query:
        raise AssertionError("OIDC issuer must not have a query")
    u = urllib.parse.urlsplit(_cfg.redirect_uri)
    if u.path != "/auth-oidc-callback" or u.query:
        raise AssertionError("OIDC redirect_uri must end in /auth-oidc-callback")
    _CLEANUP_CRON = sirepo.cron.CronTask(60 * 60, _cleanup, None)


async def _cleanup(_):
    with sirepo.quest.start() as qcall:
        m = qcall.auth_db.model("AuthOidcLogin")
        m.query().filter(type(m).expires < sirepo.srtime.utc_now()).delete()


def _cfg_url(value):
    u = urllib.parse.urlsplit(value)
    if (
        u.scheme not in ("https", "http")
        or not u.hostname
        or u.username
        or u.password
        or u.fragment
        or (u.scheme != "https" and u.hostname not in ("localhost", "127.0.0.1", "::1"))
    ):
        raise AssertionError("OIDC URLs require HTTPS (HTTP allowed only on loopback)")
    return value


def _client():
    return AsyncOAuth2Client(
        _cfg.client_id,
        _cfg.client_secret,
        token_endpoint_auth_method=_cfg.token_endpoint_auth_method,
        redirect_uri=_cfg.redirect_uri,
        scope="openid email profile",
        code_challenge_method="S256",
        timeout=10,
        follow_redirects=False,
    )


def _email_user(qcall, claims):
    subject = claims.get("sub")
    email = claims.get("email")
    if (
        not isinstance(subject, str)
        or not subject
        or len(subject) > 255
        or not isinstance(email, str)
        or len(email) > 255
        or not pyisemail.is_email(email)
        or claims.get("email_verified") is not True
    ):
        raise sirepo.util.Forbidden("OIDC login requires a subject and verified email")
    users = qcall.auth_db.model(UserModel)
    email = email.lower()
    user = users.unchecked_search_by(user_name=email)
    if not user:
        user = users.unchecked_search_by(unverified_email=email)
        if user and user.user_name not in (None, email):
            raise sirepo.util.Forbidden("OIDC email conflicts with an account")
    return email, user


def _registration_or_login(qcall, claims, sim_type):
    email, user = _email_user(qcall, claims)
    if user and not qcall.auth.need_complete_registration(user):
        return _login(qcall, claims, sim_type)
    state = secrets.token_urlsafe(32)
    qcall.auth_db.model(
        "AuthOidcLogin",
        state=state,
        nonce="",
        verifier="",
        email=email,
        simulation_type=sim_type,
        expires=sirepo.srtime.utc_now() + _LOGIN_LIFETIME,
    ).save()
    qcall.cookie.set_value(_COOKIE_REGISTRATION, state)
    raise sirepo.util.Redirect(sirepo.uri.local_route(sim_type, "oidcRegistration"))


def _login(
    qcall,
    claims,
    sim_type,
    display_name=None,
    moderation_reason=None,
    want_redirect=True,
):
    email, user = _email_user(qcall, claims)
    if not user or not user.user_name:
        if not user:
            user = qcall.auth_db.model(UserModel).new(unverified_email=email)
        user.user_name = email
        user.save()
    if not qcall.auth.user_if_logged_in(qcall.auth.METHOD_GUEST):
        # Preserve normal guest migration without linking other browser accounts.
        qcall.auth.reset_state()
    qcall.auth.login(
        this_module,
        model=user,
        sim_type=sim_type,
        want_redirect=want_redirect,
        display_name=display_name,
        moderation_reason=moderation_reason,
    )


async def _metadata(client):
    try:
        response = await client.request(
            "GET",
            _cfg.issuer.rstrip("/") + "/.well-known/openid-configuration",
            withhold_token=True,
        )
        response.raise_for_status()
        metadata = response.json()
        if metadata["issuer"] != _cfg.issuer:
            raise sirepo.util.Forbidden("OIDC discovery issuer mismatch")
        for key in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
            _cfg_url(metadata[key])
        return metadata
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AssertionError) as e:
        pkdlog("OIDC discovery failed: {}", type(e).__name__)
        raise sirepo.util.Forbidden("OIDC discovery failed") from None


def _require_http_get(qcall):
    if qcall.sreq.http_method != "GET" or "http_request_uri" not in qcall.sreq:
        raise sirepo.util.Forbidden("OIDC login requires HTTP GET navigation")
