# -*- coding: utf-8 -*-
"""request input parsing

:copyright: Copyright (c) 2018 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdexc, pkdlog, pkdp
import sirepo.sim_data
import sirepo.srschema
import sirepo.template
import sirepo.util


def init_module(**imports):
    # import simulation_db

    sirepo.util.setattr_imports(imports)


def parse_json(qcall):
    d = qcall.http_data_uget()
    if d:
        return d
    if not qcall.sreq.content_type_eq("application/json"):
        raise sirepo.util.BadRequest(
            "Content-Type={} must be application/json",
            qcall.sreq.header_uget("Content-Type"),
        )
    # Adapted from flask.wrappers.Request.get_json
    # We accept a request charset against the specification as
    # certain clients have been using this in the past.  This
    # fits our general approach of being nice in what we accept
    # and strict in what we send out.
    return simulation_db.json_load(
        qcall.sreq.body_as_bytes(),
        encoding=qcall.sreq.content_type_encoding(),
    )


def parse_post(qcall, kwargs):
    """Parse a post augmented by inline args

    Arguments are either `bool` or another `object`.
    If a bool and True, the value is parsed from `req_data`.
    If another `object`, the value is parsed as is, setting
    on `req_data`.

    The names of the args are the keys of the return value.

    Args:
        req_data (PKDict): input values [`parse_json`]
        type (object): `assert_sim_type`
        file_type (object): `sirepo.util.secure_filename`
        filename (object): `sirepo.util.secure_filename`
        folder (object): `parse_folder`
        id (object): `parse_sid`
        model (object): `parse_model`
        name (object): `parse_name`
        template (object): `sirepo.template.import_module`
    Returns:
        PKDict: with arg names set to parsed values
    """
    res = PKDict(qcall=qcall)
    r = kwargs.pkdel("req_data")
    if r is None:
        r = parse_json(qcall)
    if kwargs.pkdel("fixup_old_data"):
        r = simulation_db.fixup_old_data(r, qcall=qcall)[0]
    res.pkupdate(req_data=r)
    kwargs.pksetdefault(type=True)

    def _type(v):
        from sirepo import auth

        assert not isinstance(v, bool), "missing type in params/post={}".format(kwargs)
        qcall.auth.check_sim_type_role(v)
        res.sim_data = sirepo.sim_data.get_class(v)
        return v

    for x in (
        # must be first
        ("type", ("simulationType",), _type),
        ("file_type", ("file_type", "fileType"), sirepo.util.secure_filename),
        ("filename", ("filename", "fileName"), sirepo.util.secure_filename),
        ("folder", ("folder",), sirepo.srschema.parse_folder),
        ("id", ("simulationId",), lambda a: res.sim_data.parse_sid(r)),
        ("model", ("report",), lambda a: res.sim_data.parse_model(r)),
        ("name", ("name",), sirepo.srschema.parse_name),
        # will break if someone passes a template as a value
        ("template", ("template",), lambda a: sirepo.template.import_module(res.type)),
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
    if (
        kwargs.pkdel("check_sim_exists")
        and not simulation_db.sim_data_file(res.type, res.id, qcall=qcall).exists()
    ):
        raise sirepo.util.NotFound("type={} sid={} does not exist", res.type, res.id)
    for k in list(kwargs.keys()):
        if isinstance(kwargs[k], PKDict):
            s = kwargs.pkdel(k)
            n = s["name"] if "name" in s else k
            v = r[n] if n in r else None
            assert (
                v is not None or "optional" in s and s["optional"] == True
            ), "required param={} missing in post={}".format(k, r)
            if v is not None:
                res[n] = v

    assert not kwargs, "unexpected kwargs={}".format(kwargs)
    return res
