from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp


class AnalysisDriverBase(PKDict):
    pass


def get_analysis_driver(catalog_name=None, req_body=None):
    if not catalog_name:
        assert req_body, "need catalog_name or req_body to get analysis driver"
        if _analysis_driver_not_needed(req_body):
            return

    k = PKDict(
        catalog_name=catalog_name or req_body.pknested_get("data.args.catalogName"),
    )
    return _class_for_catalog_name(k.catalog_name)(k)


def _analysis_driver_not_needed(req_body):
    return "args" not in req_body.data or "catalogName" not in req_body.data.args


def _class_for_catalog_name(catalog_name):
    import importlib
    import sys

    n = catalog_name.upper()
    m = f"sirepo.raydata.analysis_driver.{n}"
    if m not in sys.modules:
        importlib.import_module(m)
    return getattr(sys.modules.get(m), n)
