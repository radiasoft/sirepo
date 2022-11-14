# -*- coding: utf-8 -*-
"""Moderate user roles

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkconfig
from pykern.pkdebug import pkdexc, pkdp, pkdlog
from pykern.pkcollections import PKDict
from pykern import pkjinja
import sirepo.quest
import sirepo.api_perm
import sirepo.auth
import sirepo.auth_db
import sirepo.auth_role
import sirepo.feature_config
import sirepo.simulation_db
import sirepo.smtp
import sirepo.uri
import sirepo.uri_router
import sqlalchemy

_STATUS_TO_SUBJECT = None

_cfg = None

_ACTIVE = frozenset(
    [
        sirepo.auth_role.ModerationStatus.CLARIFY,
        sirepo.auth_role.ModerationStatus.PENDING,
    ]
)


class API(sirepo.quest.API):
    @sirepo.quest.Spec(
        "require_adm", token="AuthModerationToken", status="AuthModerationStatus"
    )
    def api_admModerate(self):
        def _send_moderation_status_email(info):
            sirepo.smtp.send(
                recipient=info.user_name,
                subject=_STATUS_TO_SUBJECT[info.status].format(info.app_name),
                body=pkjinja.render_resource(
                    f"auth_role_moderation/{info.status}_email",
                    PKDict(
                        app_name=info.app_name,
                        display_name=info.display_name,
                        link=self.absolute_uri(
                            self.uri_for_app_root(
                                sirepo.auth_role.sim_type(info.role),
                            ),
                        ),
                    ),
                ),
            )

        def _set_moderation_status(info):
            if info.status == "approve":
                sirepo.auth_db.UserRole.add_roles(qcall=self, roles=[info.role])
            sirepo.auth_db.UserRoleInvite.set_status(
                qcall=self,
                role=info.role,
                status=info.status,
                moderator_uid=info.moderator_uid,
            )

        req = self.parse_post(type=False)
        i = sirepo.auth_db.UserRoleInvite.search_by(token=req.req_data.token)
        if not i:
            pkdlog(f"No record in UserRoleInvite for token={req.req_data.token}")
            raise sirepo.util.UserAlert(
                "Could not find the moderation request; "
                "refresh your browser to get the latest moderation list.",
            )
        p = PKDict(
            app_name=sirepo.simulation_db.SCHEMA_COMMON.appInfo[
                sirepo.auth_role.sim_type(i.role)
            ].longName,
            role=i.role,
            status=req.req_data.status,
            moderator_uid=self.auth.logged_in_user(),
        )
        pkdlog("status={} uid={} role={} token={}", p.status, i.uid, i.role, i.token)
        with self.auth.logged_in_user_set(uid=i.uid, method=self.auth.METHOD_EMAIL):
            p.pkupdate(
                display_name=self.auth.user_display_name(i.uid),
                user_name=self.auth.logged_in_user_name(),
            )
            _set_moderation_status(p)
            _send_moderation_status_email(p)
        return self.reply_ok()

    @sirepo.quest.Spec("require_adm")
    def api_admModerateRedirect(self):
        def _type():
            x = sirepo.feature_config.auth_controlled_sim_types()
            res = sorted(sirepo.feature_config.cfg().sim_types - x)
            return res[0] if res else sorted(x)[0]

        raise sirepo.util.Redirect(
            self.absolute_uri(
                sirepo.uri.local_route(_type(), route_name="admRoles"),
            ),
        )

    @sirepo.quest.Spec("require_adm")
    def api_getModerationRequestRows(self):
        return self.reply_json(
            PKDict(
                rows=sirepo.auth_db.UserRoleInvite.get_moderation_request_rows(self),
            ),
        )

    @sirepo.quest.Spec(
        "allow_sim_typeless_require_email_user", reason="AuthModerationReason"
    )
    def api_saveModerationReason(self):
        def _send_request_email(info):
            sirepo.smtp.send(
                recipient=_cfg.moderator_email,
                subject=f"{info.sim_type} Access Request",
                body=pkjinja.render_resource(
                    "auth_role_moderation/moderation_email", info
                ),
            )

        req = self.parse_post()
        u = self.auth.logged_in_user()
        r = sirepo.auth_role.for_sim_type(req.type)
        with sirepo.util.THREAD_LOCK:
            if sirepo.auth_db.UserRole.has_role(qcall=self, role=r):
                raise sirepo.util.Redirect(sirepo.uri.local_route(req.type))
            try:
                sirepo.auth_db.UserRoleInvite(
                    uid=u,
                    role=r,
                    status=sirepo.auth_role.ModerationStatus.PENDING,
                    token=sirepo.util.random_base62(32),
                ).save()
            except sqlalchemy.exc.IntegrityError as e:
                pkdlog(
                    "Error={} saving UserRoleInvite for uid={} role={} stack={}",
                    e,
                    u,
                    r,
                    pkdexc(),
                )
                raise sirepo.util.UserAlert(
                    f"You've already submitted a moderation request.",
                )

        l = self.absolute_uri(self.uri_for_api("admModerateRedirect"))
        _send_request_email(
            PKDict(
                display_name=self.auth.user_display_name(u),
                email_addr=self.auth.logged_in_user_name(),
                link=l,
                reason=req.req_data.reason,
                role=sirepo.auth_role.for_sim_type(req.type),
                sim_type=req.type,
                uid=u,
            ).pkupdate(self.user_agent_headers())
        )
        return self.reply_ok()


def raise_control_for_user(qcall, uid, role, sim_type):
    s = sirepo.auth_db.UserRoleInvite.get_status(qcall=qcall, role=role)
    if s in _ACTIVE:
        raise sirepo.util.SRException("moderationPending", PKDict(sim_type=sim_type))
    if s == sirepo.auth_role.ModerationStatus.DENY:
        sirepo.util.raise_forbidden(f"uid={uid} role={role} already denied")
    assert s is None, f"Unexpected status={s} for uid={uid} and role={role}"
    qcall.auth.require_email_user()
    raise sirepo.util.SRException("moderationRequest", PKDict(sim_type=sim_type))


def init_apis(*args, **kwargs):
    global _cfg, _STATUS_TO_SUBJECT

    _cfg = pkconfig.init(
        moderator_email=pkconfig.Required(
            str, "The email address to send moderation emails to"
        ),
    )
    _STATUS_TO_SUBJECT = PKDict(
        approve="{} Access Request Approved",
        # TODO(robnagler) should we send an email when moderation pending?
        # For completeness
        pending=None,
        clarify="Sirepo {}: Additional Info?",
        deny="{} Access Request Denied",
    )
    x = frozenset(_STATUS_TO_SUBJECT.keys())
    if x != sirepo.auth_role.ModerationStatus.VALID_SET:
        raise AssertionError(
            f"{x} not same as {sirepo.auth_role.ModerationStatus.VALID_SET}"
        )
