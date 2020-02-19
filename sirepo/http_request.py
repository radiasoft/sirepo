# -*- coding: utf-8 -*-
u"""request input parsing

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import flask
import sirepo.api_perm
import sirepo.sim_data
import sirepo.template
import sirepo.util
import sirepo.srschema
import user_agents
import werkzeug

_API_PERM_ATTR = 'sirepo_http_request_api_perm'

_SIM_TYPE_ATTR = 'sirepo_http_request_sim_type'

_POST_ATTR = 'sirepo_http_request_post'

_PROTECTED_CODES = ('flash', 'elegant') # TODO(e-carlin): rm elegant


def init(**imports):
    sirepo.util.setattr_imports(imports)


def is_spider():
    return user_agents.parse(flask.request.headers.get('User-Agent')).is_bot


def parse_json():
    d = set_post()
    if d:
        return d
    req = flask.request
    if req.mimetype != 'application/json':
        sirepo.util.raise_bad_request(
            'content-type is not application/json: mimetype={}',
            req.mimetype,
        )
    # Adapted from flask.wrappers.Request.get_json
    # We accept a request charset against the specification as
    # certain clients have been using this in the past.  This
    # fits our general approach of being nice in what we accept
    # and strict in what we send out.
    return simulation_db.json_load(
        req.get_data(cache=False),
        encoding=req.mimetype_params.get('charset'),
    )


def parse_params(**kwargs):
    return parse_post(req_data=PKDict(), **kwargs)


def parse_post(**kwargs):
    """Parse a post augmented by inline args

    Arguments are either `bool` or another `object`.
    If a bool and True, the value is parsed from `req_data`.
    If another `object`, the value is parsed as is, setting
    on `req_data`.

    The names of the args are the keys of the return value.

    Args:
        req_data (PKDict): input values [`parse_json`]
        type (object): `assert_sim_type`
        file_type (object): `werkzeug.secure_filename`
        filename (object): `werkzeug.secure_filename`
        folder (object): `parse_folder`
        id (object): `parse_sid`
        model (object): `parse_model`
        name (object): `parse_name`
        template (object): `sirepo.template.import_module`
    Returns:
        PKDict: with arg names set to parsed values
    """
    res = PKDict()
    kwargs = PKDict(kwargs)
    r = kwargs.pkdel('req_data')
    if r is None:
        r = parse_json()
    if kwargs.pkdel('fixup_old_data'):
        r = simulation_db.fixup_old_data(r)[0]
    res.pkupdate(req_data=r)
    kwargs.pksetdefault(type=True)

    def t(v):
        assert not isinstance(v, bool), \
            'missing type in params/post={}'.format(kwargs)
        v = sirepo.template.assert_sim_type(v)
        # flask.g API is very limited but do this in order to
        # maintain explicit coupling of _SIM_TYPE_ATTR
        set_sim_type(v)
        res.sim_data = sirepo.sim_data.get_class(v)
        return v

    for x in (
        # must be first
        ('type', ('simulationType',), t),
        ('file_type', ('file_type', 'fileType'), werkzeug.secure_filename),
        ('filename', ('filename', 'fileName'), werkzeug.secure_filename),
        ('folder', ('folder',), sirepo.srschema.parse_folder),
        ('id', ('simulationId',), lambda a: res.sim_data.parse_sid(r)),
        ('model', ('report',), lambda a: res.sim_data.parse_model(r)),
        ('name', ('name',), sirepo.srschema.parse_name),
        # will break if someone passes a template as a value
        ('template', ('template',), lambda a: sirepo.template.import_module(res.type)),
    ):
        n, z, f = x
        v = kwargs.pkdel(n)
        if v is None:
            continue
        if isinstance(v, bool):
            if not v:
                continue
            for k in z:
                if k in r:
                    v = r[k]
                    break
        else:
            r[z[0]] = v
        res[n] = f(v)
    if kwargs.pkdel('check_sim_exists') \
        and not simulation_db.sim_data_file(res.type, res.id).exists():
        sirepo.util.raise_not_found('type={} sid={} does not exist', res.type, res.id)
    assert not kwargs, \
        'unexpected kwargs={}'.format(kwargs)
    if flask.g.get(_API_PERM_ATTR) == sirepo.api_perm.APIPerm.REQUIRE_USER:
    # if flask.g.get(_API_PERM_ATTR) != sirepo.api_perm.APIPerm.ALLOW_VISITOR:
        _check_permissions(res.type)
    return res


def set_api_perm(perm):
    """Interface for uri_router"""
    return _set_flask_g(_API_PERM_ATTR, perm)


def set_post(data=None):
    """Interface for uri_router"""
    return _set_flask_g(_POST_ATTR, data)


def set_sim_type(sim_type):
    """Interface for uri_router"""
    if not sirepo.template.is_sim_type(sim_type):
        # Don't change sim_type unless we have a valid one
        return None
    res = flask.g.pop(_SIM_TYPE_ATTR, None)
    flask.g.setdefault(_SIM_TYPE_ATTR, sim_type)
    return res


def sim_type(value=None):
    """Return value or request's sim_type

    Args:
        value (str): will be validated if not None
    Returns:
        str: sim_type or possibly None
    """
    if value:
        return sirepo.template.assert_sim_type(value)
    return flask.g.get(_SIM_TYPE_ATTR)


def _check_permissions(simulation_type):
    import sirepo.auth
    import sirepo.auth_db
    if simulation_type in _PROTECTED_CODES and \
       simulation_type not in sirepo.auth_db.UserRole.search_all_for_column(
           'role',
           uid=sirepo.auth.logged_in_user(),
       ):
        sirepo.util.raise_forbidden(
            'you do not have permission to use {}'.format(simulation_type),
        )


def _set_flask_g(key, value):
    # Always remove data (if there)
    res = flask.g.pop(key, None)
    if value is not None:
        flask.g.setdefault(key, value)
    return res
