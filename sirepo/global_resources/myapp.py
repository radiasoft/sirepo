"""Global resources for myapp (tests).

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
import sirepo.global_resources


class Allocator(sirepo.global_resources.AllocatorBase):
    def _get(self):
        r = self._manager.get_resources(PKDict(public_ports=1, ips=1, ports=2))
        return PKDict(
            public_port=r.public_ports[0],
            ip=str(r.ips[0]),
            ports=r.ports,
        )

    def _redact_for_gui(self, resources):
        return PKDict(public_port=resources.public_port)
