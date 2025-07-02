"""Moderate user roles

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern import pkjinja
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdexc, pkdp, pkdlog
import datetime
import getpass
import sirepo.auth_role
import sirepo.const
import sirepo.feature_config
import sirepo.quest
import sirepo.simulation_db
import sirepo.smtp
import sirepo.uri
import sirepo.util
import sqlalchemy.exc

_STATUS_TO_SUBJECT = PKDict(
    approve="Access Request Approved",
    # TODO(robnagler) should we send an email when moderation pending?
    # For completeness
    pending=None,
    clarify="Additional Info?",
    deny="Access Request Denied",
)

_cfg = None

_ACTIVE = frozenset(
    (
        sirepo.auth_role.ModerationStatus.CLARIFY,
        sirepo.auth_role.ModerationStatus.PENDING,
    )
)


class API(sirepo.quest.API):
    @sirepo.quest.Spec(
        "require_adm", uid="Str", role="Str", status="AuthModerationStatus"
    )
    async def api_admModerate(self):
        def _role_info(role, status):
            s = sirepo.simulation_db.SCHEMA_COMMON
            rv = PKDict(
                # TODO(robnagler) maybe save the sim_type in the client so
                # when there's a redirect, it goes back to the app you were in
                # when you registered?
                moderator_uid=self.auth.logged_in_user(),
                product_name=s.productInfo.shortName,
                role=role,
                status=status,
            )
            if role == sirepo.auth_role.ROLE_PLAN_TRIAL:
                e = sirepo.util.plan_role_expiration(role)
                return rv.pkupdate(
                    additional_text=(
                        f"Your free trial ends on {e.strftime('%d %B %Y')}."
                        if e
                        else ""
                    ),
                    expiration=e,
                    link=self.absolute_uri(self.uri_for_app_root()),
                    role_display_name="Trial",
                )
            t = sirepo.auth_role.sim_type(role)
            return rv.pkupdate(
                role_display_name=s.appInfo[t].longName,
                link=self.absolute_uri(self.uri_for_app_root(t)),
            )

        def _send_moderation_status_email(info):
            sirepo.smtp.send(
                recipient=info.user_name,
                subject=f"Sirepo {info.role_display_name}: {_STATUS_TO_SUBJECT[info.status]}",
                body=pkjinja.render_resource(
                    f"auth_role_moderation/{info.status}_email",
                    PKDict(
                        additional_text=info.get("additional_text"),
                        product_name=info.product_name,
                        role_display_name=info.role_display_name,
                        display_name=info.display_name,
                        link=info.link,
                    ),
                ),
            )

        def _set_moderation_status(info):
            if info.status == "approve":
                m = self.auth_db.model("UserRole")
                if info.role in sirepo.auth_role.PLAN_ROLES:
                    m.add_plan(info.role, info.uid)
                else:
                    # No expiration for non-plan roles
                    m.add_roles([info.role], info.uid)
            self.auth_db.model("UserRoleModeration").set_status(
                role=info.role,
                uid=info.uid,
                status=info.status,
                moderator_uid=info.moderator_uid,
            )

        req = self.parse_post(type=False)
        i = self.auth_db.model("UserRoleModeration").unchecked_search_by(
            uid=req.req_data.uid,
            role=req.req_data.role,
        )
        if not i:
            pkdlog(
                "UserRoleModeration not found uid={} role={}",
                req.req_data.uid,
                req.req_data.role,
            )
            raise sirepo.util.UserAlert(
                "Could not find the moderation request; "
                + "refresh your browser to get the latest moderation list.",
                "UserRoleModeration not found uid={} role={}",
                req.req_data.uid,
                req.req_data.role,
            )
        p = _role_info(i.role, req.req_data.status)
        pkdlog("status={} uid={} role={}", p.status, i.uid, i.role)
        # Force METHOD_EMAIL. We are sending them an email so we will
        # need an email for them. We only have emails for METHOD_EMAIL
        # users.
        with self.auth.logged_in_user_set(uid=i.uid, method=self.auth.METHOD_EMAIL):
            u = self.auth.user_name(i.uid)
            # Sanity check. user_name() should blow up above if METHOD_EMAIL is not
            # correct but good to be sure.
            if not u:
                raise AssertionError(
                    f"auth method={self.auth.METHOD_EMAIL} is incorrect for uid={i.uid}"
                )
            p.pkupdate(
                display_name=self.auth.user_display_name(i.uid),
                uid=i.uid,
                user_name=u,
            )
            _set_moderation_status(p)
            _send_moderation_status_email(p)
        return self.reply_ok()

    @sirepo.quest.Spec("require_adm")
    async def api_admModerateRedirect(self):
        raise sirepo.util.Redirect(
            sirepo.uri.local_route(sirepo.util.first_sim_type(), route_name="admRoles"),
        )

    @sirepo.quest.Spec("require_adm")
    async def api_getModerationRequestRows(self):
        return self.reply_dict(
            PKDict(
                rows=_datetime_to_str(
                    self.auth_db.model(
                        "UserRoleModeration"
                    ).get_moderation_request_rows()
                ),
            ),
        )

    @sirepo.quest.Spec(
        "allow_sim_typeless_require_email_user", reason="AuthModerationReason"
    )
    async def api_saveModerationReason(self):
        req = self.parse_post()
        return save_moderation_reason(
            self,
            self.auth.logged_in_user(),
            req.type,
            req.req_data.get("reason"),
        )


def _datetime_to_str(rows):
    for r in rows:
        for k, v in r.items():
            if isinstance(v, datetime.datetime):
                r[k] = str(v)
    return rows


def raise_control_for_user(qcall, uid, role):
    s = qcall.auth_db.model("UserRoleModeration").get_status(uid=uid, role=role)
    if s in _ACTIVE:
        raise sirepo.util.SRException("moderationPending", None)
    if s == sirepo.auth_role.ModerationStatus.DENY:
        raise sirepo.util.Forbidden(f"uid={uid} role={role} already denied")
    assert s is None, f"Unexpected status={s} for uid={uid} and role={role}"
    qcall.auth.require_email_user()
    raise sirepo.util.SRException("moderationRequest", PKDict(role=role))


def init_apis(*args, **kwargs):
    global _cfg

    _cfg = pkconfig.init(
        moderator_email=pkconfig.RequiredUnlessDev(
            f"{getpass.getuser()}+moderator@{sirepo.const.LOCALHOST_FQDN}",
            str,
            "The email address to send moderation emails to",
        ),
    )
    x = frozenset(_STATUS_TO_SUBJECT.keys())
    if x != sirepo.auth_role.ModerationStatus.VALID_SET:
        raise AssertionError(
            f"{x} not same as {sirepo.auth_role.ModerationStatus.VALID_SET}"
        )


def save_moderation_reason(qcall, uid, sim_type, reason):
    r = sirepo.auth_role.ROLE_PLAN_TRIAL
    # SECURITY: type has been validated to be a known sim type. If it is
    # not in moderated_sim_types then we know the user is just requesting
    # access to start using Sirepo (ROLE_PLAN_TRIAL).
    if sim_type in sirepo.feature_config.cfg().moderated_sim_types:
        r = sirepo.auth_role.for_sim_type(sim_type)
    if qcall.auth_db.model("UserRole").has_active_role(role=r, uid=uid):
        raise sirepo.util.Redirect(sirepo.uri.local_route(sim_type))
    if qcall.auth_db.model("UserRole").has_expired_role(role=r, uid=uid):
        raise AssertionError(
            f"uid={uid} trying to request moderation for expired role={r}"
        )
    try:
        qcall.auth_db.model(
            "UserRoleModeration",
            uid=uid,
            role=r,
            status=sirepo.auth_role.ModerationStatus.PENDING,
        ).save()
    except sqlalchemy.exc.IntegrityError as e:
        pkdlog(
            "Error={} saving UserRoleModeration for uid={} role={} stack={}",
            e,
            uid,
            r,
            pkdexc(),
        )
        raise sirepo.util.UserAlert(
            "You've already submitted a moderation request.",
        )
    l = qcall.absolute_uri(qcall.uri_for_api("admModerateRedirect"))
    if not reason or len(reason.strip()) == 0:
        raise sirepo.util.UserAlert("Reason for requesting access not provided")
    sirepo.smtp.send(
        recipient=_cfg.moderator_email,
        subject=f"{sim_type} Access Request",
        body=pkjinja.render_resource(
            "auth_role_moderation/moderation_email",
            PKDict(
                display_name=qcall.auth.user_display_name(uid),
                email_addr=qcall.auth.logged_in_user_name(),
                link=l,
                reason=reason,
                role=r,
                sim_type=sim_type,
                uid=uid,
            ).pkupdate(qcall.user_agent_headers()),
        ),
    )
    return qcall.reply_ok()
