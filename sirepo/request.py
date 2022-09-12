"""Requests hold context for API calls

:copyright: Copyright (c) 2022 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


class Base(PKDict):
    """Holds context for incoming requests"""

    def method_is_post(self):
        return self.method == "POST"

    def unchecked_header(self, key):
        return self.headers.get(key)
