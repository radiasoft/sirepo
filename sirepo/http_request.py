# -*- coding: utf-8 -*-
u"""request input parsing

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
from sirepo import util
import flask
import sirepo.template
import user_agents

_PARAM_MAP = PKDict(
    file_type='file_type',
    filename='filename',
    id='simulationId',
    model='report',
    template='template',
    type='simulationType',
)

def is_spider():
    return user_agents.parse(flask.request.headers.get('User-Agent')).is_bot


def parse_json():
    from sirepo import simulation_db

    #POSIT: uri_router.call_api
    if hasattr(flask.g, 'sirepo_call_api_data') and flask.g.sirepo_call_api_data:
#TODO(robnagler) this probably should clear the data
        return flask.g.sirepo_call_api_data
    req = flask.request
    if req.mimetype != 'application/json':
        util.raise_bad_request(
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
    return parse_json(**a)


def parse_post(**kwargs):
    import sirepo.sim_data
    import sirepo.simulation_db
    import sirepo.template

    res = PKDict()
    k = PKDict(kwargs)
    r = k.pkdel('req_data')
    if not r:
        r = http_request.parse_json()
        if k.pkdel('req_validate'):
            r = simulation_db.fixup_old_data(r)[0]
    res.req_data = r
    res.sim_data = sirepo.sim_data.get_class(res.type)
    flask.g.sirepo_sim_type = r.simulationType
    if k.pkdel('id'):
        res.id = res.sim_data.parse_sid(r)
    if k.pkdel('filename'):
        res.filename = werkzeug.secure_filename(r.get('fileName') or r.get('filename'))
    if k.pkdel('file_type'):
        res.file_type = werkzeug.secure_filename(r.get('file_type') or r.get('fileType'))
    if k.pkdel('model'):
        res.model = res.sim_data.parse_model(r)
    if k.pkdel('template'):
        res.template = sirepo.template.import_module(sim.type)
    if k:
        # always parse type, but allow people to pass as param
        k.pkdel('type')
        assert not k, \
            'unexpected kwargs={}'.format(k)
    return res
