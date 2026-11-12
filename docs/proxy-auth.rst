Reverse-proxy authentication
============================

Use the ``header`` authentication method when a trusted reverse proxy handles
single sign-on, such as OpenID Connect (OIDC). The proxy authenticates the user
and supplies their identity to Sirepo's login endpoint. Sirepo then maintains
its own session cookie. Sirepo does not perform the OIDC flow or validate OIDC
tokens.

Sirepo configuration
--------------------

Configure Sirepo with::

    SIREPO_AUTH_METHODS=header
    SIREPO_AUTH_HEADER_TKN=<a-long-random-shared-secret>
    SIREPO_AUTH_HEADER_USERNAME_HEADER=X-Sirepo-User
    SIREPO_AUTH_HEADER_TOKEN_HEADER=X-Sirepo-Auth-Token

The header names shown are the defaults and are case-insensitive. Set the same
shared secret in Sirepo and the proxy. Keep it out of source control and logs.

Proxy configuration
-------------------

The proxy must:

* Remove any client-supplied identity and shared-secret headers, including
  duplicates, and overwrite them using only its authenticated OIDC session.
* Authenticate requests to ``/auth-header-login/<simulation_type>``, where
  ``simulation_type`` is an enabled Sirepo application.
* Supply exactly one username and one shared-secret header to that endpoint.
  Use a stable, verified identity, normally the user's email address. Do not
  use an unverified or user-editable identity claim.
* Restrict access to the Sirepo backend to trusted proxies only and protect
  the proxy-to-backend connection (for example, with TLS or a private network).
* Remove any OIDC bearer Authorization header before forwarding to Sirepo;
  Sirepo does not validate OIDC tokens.

After OIDC authentication, an HAProxy backend can set the headers as follows,
assuming the OIDC integration has populated ``txn.oidc_username``::

    http-request del-header X-Sirepo-User
    http-request del-header X-Sirepo-Auth-Token
    http-request del-header Authorization
    http-request set-header X-Sirepo-User %[var(txn.oidc_username)]
    http-request set-header X-Sirepo-Auth-Token <the-shared-secret>

These rules alone do not implement OIDC: configure the authentication integration
to deny or redirect unauthenticated requests before they reach this backend.

Other Sirepo endpoints ignore the identity headers, so the proxy may either
send them only to the login endpoint or include them on all forwarded requests.
If bot clients use Basic authentication, route them separately to preserve
their Authorization header.

Accounts and access
-------------------

Usernames are matched case-insensitively. To reuse existing accounts, supply
their full username; Sirepo does not append an email domain. Usernames must be
nonempty, at most 255 characters, and contain no whitespace, nonprintable
characters, or commas.

Existing accounts retain their simulations, roles, and display name. New
accounts are created automatically, and users complete registration by entering
a display name. Automatic account creation requires
``SIREPO_FEATURE_CONFIG_IS_REGISTRATION_MODERATED=0``. With registration
moderation enabled, only accounts with completed registration can log in.

New accounts receive Sirepo's standard roles, including ``premium`` when the
``payments`` API module is not enabled. Existing account roles are unchanged.
Single sign-on does not bypass role, plan, or application-access requirements.

Sessions and logout
-------------------

When ``header`` is the only login method, the Sirepo login page automatically
sends the browser to the proxy login endpoint. With multiple methods, users
select ``Sign in with Single Sign-On``. After login, Sirepo redirects to
registration or the application.

If the Sirepo session cookie is lost, users log in again through the same flow.
A valid OIDC session normally avoids another password prompt. API clients and
WebSocket connections must first establish a Sirepo cookie session through the
HTTP login endpoint; supplying identity headers on ordinary requests is not
sufficient.

An existing Sirepo header-auth session takes precedence over proxy headers,
even at the login endpoint. To switch accounts, log out of Sirepo and select
the new identity at the proxy before logging in again.

Sirepo and OIDC sessions are independent. Sirepo logout does not end the OIDC
session, and OIDC logout or expiry does not invalidate the Sirepo cookie.
Configure both logout flows for single sign-out.

If access must end when the OIDC session ends, enforce authentication at the
proxy for HTTP requests and WebSocket upgrades, and close existing WebSocket
connections on logout or expiry. Removing identity headers does not revoke a
Sirepo session. Health checks and intentionally public routes may be exempted
from OIDC without granting access to protected Sirepo APIs.
