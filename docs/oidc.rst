OpenID Connect authentication
=============================

Use the ``oidc`` authentication method to sign in through an OpenID Connect
provider. Sirepo handles the authorization-code flow directly using Authlib;
a reverse proxy does not need to authenticate users or supply identity headers.
One provider is configured per Sirepo deployment.

Provider setup
--------------

Register Sirepo as a confidential web client with authorization-code support
and PKCE using ``S256``. The authorization response must use query parameters
on a GET callback (not ``form_post``). Register this callback URL, substituting
the public Sirepo origin::

    https://sirepo.example.org/auth-oidc-callback

The provider must support discovery and return a signed ID token containing
``sub``, ``email``, and a boolean ``email_verified=true``. Sirepo requests the
``openid email profile`` scopes. Supported ID-token signing algorithms are
RS256, RS384, RS512, ES256, ES384, and ES512.
Email claims must be in the ID token; Sirepo does not call the UserInfo endpoint.

Microsoft Entra ID
~~~~~~~~~~~~~~~~~

Entra ID compatibility has not been established. Its standard ID-token claims
do not guarantee ``email_verified=true``, which this implementation requires.
Microsoft also warns that the ``email`` claim is mutable and not guaranteed
correct. Do not remove the verified-email check or substitute
``preferred_username`` without defining the deployment's identity trust policy.
See Microsoft's `ID token claims reference
<https://learn.microsoft.com/en-us/entra/identity-platform/id-token-claims-reference>`_.
An Entra deployment would also need a tenant-specific issuer matching discovery
and tokens, rather than a ``common`` or ``organizations`` issuer.

Sirepo configuration
--------------------

Configure the provider and client credentials::

    SIREPO_AUTH_METHODS=oidc
    SIREPO_AUTH_OIDC_ISSUER=https://idp.example.org
    SIREPO_AUTH_OIDC_CLIENT_ID=sirepo
    SIREPO_AUTH_OIDC_CLIENT_SECRET=<client-secret>
    SIREPO_AUTH_OIDC_REDIRECT_URI=https://sirepo.example.org/auth-oidc-callback

The issuer must exactly match the provider's discovery metadata, including any
path or trailing slash. Sirepo reads discovery metadata at
``<issuer>/.well-known/openid-configuration``.
The redirect URI must exactly match the registered public callback URL.
Keep the client secret out of source control and logs.

The default token endpoint authentication method is ``client_secret_basic``.
If the provider requires credentials in the request body, set::

    SIREPO_AUTH_OIDC_TOKEN_ENDPOINT_AUTH_METHOD=client_secret_post

Provider and callback URLs require HTTPS. HTTP is allowed only for loopback
addresses for local development. When using a reverse proxy, expose the OIDC
routes on the same public origin as the application and preserve Sirepo's
session cookies.

Accounts and access
-------------------

At each login, Sirepo selects the account by the provider's verified email
address, matched case-insensitively, as with email and LDAP login. If there is no
matching registered account, Sirepo holds the verified identity in a short-lived
pending request and asks the user to enter a display name. The account and user
directory are created only when the registration form is submitted, using the
normal login and moderation path.
Existing guest accounts retain their user directory when converted to a new
OIDC account.

Only configure a provider trusted to verify ownership of every email address
it asserts. Its account enrollment, email verification, and recovery policies
are part of Sirepo's authentication trust boundary: a verified email can grant
access to an existing account and its simulations.

Email addresses are the account identifiers; Sirepo does not store a separate
mapping to the provider's subject identifier. An email change selects a different
account at the next login, and reassigning an email address can give its new
owner access to the existing account. Manage address changes and reassignment
according to your organization's account policies.

To allow registration without requesting approval, set
``SIREPO_FEATURE_CONFIG_IS_REGISTRATION_MODERATED=0``. With registration
moderation enabled, new users enter their display name and reason for requesting
access on the registration page. Requests use Sirepo's existing moderator
review and approval workflow. Registered OIDC users can also request access to
applications listed in ``SIREPO_FEATURE_CONFIG_MODERATED_SIM_TYPES``.
Existing account roles and simulations are preserved. New accounts receive
standard Sirepo roles, including premium access when payments are disabled.
Moderation governs the requested plan or application role, not account creation:
the account exists before approval. Enabling registration moderation does not
revoke roles granted by the deployment's normal role policy.
Guest simulations are transferred to the OIDC account using the same migration
as other login methods; example simulations are not transferred.

Login and sessions
------------------

With OIDC as the only login method, Sirepo's login page automatically starts
single sign-on. When other methods are enabled, users select
``Sign in with Single Sign-On``. The browser visits
``/auth-oidc-login/<simulation_type>``, signs in at the provider, and returns to
the callback. After login, Sirepo returns to the selected application or its
registration page.

Pending logins expire after ten minutes and can be used only once. Starting
another login in the same browser replaces the previous pending login; finish
the most recently started flow. Missing cookies, denied authorization, expired
requests, or invalid tokens open Sirepo's login-failure page. Start again from
the Sirepo login page.

Starting OIDC requires a logged-out or guest browser session. Log out explicitly
before switching a registered account. Pending flows are bound to that original
session: changing accounts or guests cancels them, and guest simulations can
only migrate from the guest that started the flow.

Logout cancels both pending authorization and pending registration, including
when the browser is not yet logged in and when a token exchange is in flight.
A canceled callback cannot restore a session using a saved cookie.

Pending requests are marked consumed before token exchange and deleted when the
callback finishes or fails. The row remains during network I/O so another tab
can cancel it. Starting a new login
removes the browser's previous pending request and all expired requests.
Sirepo's existing periodic-task scheduler also removes expired requests at
startup and every hour on the primary server. Expiration is checked on
callback even if cleanup has not run.

Pending registrations expire ten minutes after identity verification and are
bound to the browser's cookie. They are deleted when registration succeeds,
when a new login replaces them, or by the same periodic cleanup. An expired
registration must restart sign-in.

After login, normal Sirepo cookie sessions and permission checks apply to HTTP
and WebSocket requests. Sirepo does not store access, refresh, or ID tokens
after authentication or refresh them in the background.

Sirepo logout ends only the local Sirepo session. It does not end the provider's
SSO session, so signing in again may not require a password. Provider logout
and back-channel logout are not implemented. Similarly, provider-session expiry
does not revoke an existing Sirepo session or close open WebSocket connections.
