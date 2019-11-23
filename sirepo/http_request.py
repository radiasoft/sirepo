# -*- coding: utf-8 -*-
u"""request input parsing

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import flask
import sirepo.sim_data
import sirepo.template
import sirepo.util
import sirepo.srschema
import user_agents
import werkzeug

_PARAM_MAP = PKDict(
    file_type='file_type',
    filename='filename',
    id='simulationId',
    model='report',
    template='template',
    type='simulationType',
)

_SIM_TYPE_ATTR = 'sirepo_http_request_sim_type'

_POST_ATTR = 'sirepo_http_request_post'


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
    a = PKDict(req_data=PKDict())
    p = PKDict(kwargs)
    for k, v in _PARAM_MAP.items():
        x = p.pkdel(k)
        if x is not None:
            if k != 'template':
                a.req_data[v] = x
            a[k] = True
    assert not p, \
        'unexpected kwargs={}'.format(p)
    return parse_post(**a)


def parse_post(**kwargs):
    res = PKDict()
    k = PKDict(kwargs)
    r = k.pkdel('req_data')
    if not r:
        r = parse_json()
    if k.pkdel('fixup_old_data'):
        r = simulation_db.fixup_old_data(r)[0]
    res.pkupdate(
        req_data=r,
        type=sirepo.template.assert_sim_type(r.simulationType),
    )
    res.sim_data = sirepo.sim_data.get_class(res.type)
    # flask.g API is very limited but do this in order to
    # maintain explicit coupling of _SIM_TYPE_ATTR
    set_sim_type(res.get('type'))
    if k.pkdel('id'):
        res.id = res.sim_data.parse_sid(r)
    if k.pkdel('filename'):
        res.filename = werkzeug.secure_filename(r.get('fileName') or r.get('filename'))
    if k.pkdel('file_type'):
        res.file_type = werkzeug.secure_filename(r.get('file_type') or r.get('fileType'))
    if k.pkdel('folder'):
        res.folder = sirepo.srschema.parse_folder(r.get('folder'))
    if k.pkdel('name'):
        res.name = sirepo.srschema.parse_name(r.get('name'))
    if k.pkdel('model'):
        res.model = res.sim_data.parse_model(r)
    if k.pkdel('template'):
        res.template = sirepo.template.import_module(res.type)
    if k:
        # always parse type, but allow people to pass as param
        k.pkdel('type')
        assert not k, \
            'unexpected kwargs={}'.format(k)
    return res


def set_post(data=None):
    """Interface for uri_router"""
    # Always remove data (if there)
    res = flask.g.pop(_POST_ATTR, None)
    if data is not None:
        flask.g.setdefault(_POST_ATTR, data)
    return res


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
