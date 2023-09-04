from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp


class AnalysisDriverBase(PKDict):
    def get_analysis_driver(req_body):
        if _analysis_driver_not_needed(req_body):
            return

        k = PKDict(
            catalog_name=req_body.pknested_get("data.args.catalogName"),
        )
        if k.catalog_name == "chx":
            return CHX(k)
        elif k.catalog_name == "csx":
            return CSX(k)
        else:
            raise AssertionError(
                f"analysis driver not found for catalog_name={k.catalog_name}"
            )


class CHX(AnalysisDriverBase):
    pass


class CSX(AnalysisDriverBase):
    pass


def _analysis_driver_not_needed(req_body):
    return "args" not in req_body.data or "catalogName" not in req_body.data.args
