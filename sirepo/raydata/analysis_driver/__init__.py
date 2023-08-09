from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp


class AnalysisDriverBase(PKDict):
    def get_analysis_driver(req_body):
        try:
            k = PKDict(catalog_name=req_body.pknested_get("data.args.catalogName"))
        except KeyError:
            return None

        if k.catalog_name == "chx":
            return CHX(k)
        elif k.catalog_name == "csx":
            return CSX(k)
        else:
            # TODO(rorour)
            assert 0


class CHX(AnalysisDriverBase):
    pass


class CSX(AnalysisDriverBase):
    pass
