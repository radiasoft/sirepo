u"""Replies for all API calls.

:copyright: Copyright (c) 2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


class Base:
    pass


def init(**imports):
    import sirepo.util

    sirepo.util.setattr_imports(imports)
