class APIRequest:
    def __init__(self):
        return

    def call_api(self, name, kwargs=None, data=None):
        return uri_router.call_api(name, kwargs=kwargs, data=data)


APIBase = APIRequest


def init(**imports):
    import sirepo.util

    sirepo.util.setattr_imports(imports)
