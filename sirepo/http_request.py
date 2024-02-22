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


def parse_post(qcall, kwargs):
    """Parse a post augmented by inline args

    Arguments are either `bool` or another `object`.
    If a bool and True, the value is parsed from `req_data`.
    If another `object`, the value is parsed as is, setting
    on `req_data`.

    The names of the args are the keys of the return value.

    Args:
        req_data (PKDict): input values [`body_as_dict`]
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
        r = qcall.body_as_dict()
    if kwargs.get("fixup_old_data"):
        raise AssertionError("fixup_old_data invalid parameter")
    res.pkupdate(req_data=r)
    kwargs.pksetdefault(type=True)

    def _type(v):
        from sirepo import auth

        if isinstance(v, bool):
            raise sirepo.util.BadRequest(
                "missing simulationType in params/post={}",
                kwargs,
            )
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
            if not (v is not None or "optional" in s and s["optional"] == True):
                raise sirepo.util.BadRequest(
                    "required param={} missing in post={}",
                    k,
                    r,
                )
            if v is not None:
                res[n] = v
    if kwargs:
        raise sirepo.util.BadRequest("unexpected post parameters={}", kwargs)
    return res
