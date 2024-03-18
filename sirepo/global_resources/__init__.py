"""Resouces for simulations that are globally unique.

For example, if a port is requested that port won't conflict
with any other ports on the node.

:copyright: Copyright (c) 2023 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkconfig
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdp
import ipaddress
import sirepo.agent_supervisor_api
import sirepo.util

_MANAGER = None

_cfg = None


class AllocatorBase(PKDict):
    _allocated_resources = PKDict()

    def get(self, for_gui):
        i = self._identifier()
        return self._redact(
            for_gui, self._allocated_resources.pksetdefault(i, self._get)[i]
        )

    def _get(self):
        raise NotImplementedError("children must implement this")

    def _identifier(self):
        return "-".join((self._uid, self._sim_type, self._sid))

    def _redact(self, for_gui, resources):
        if for_gui:
            return self._redact_for_gui(resources)
        return resources

    def _redact_for_gui(self, resources):
        raise NotImplementedError("children must implement this")


class _Manager:
    def __init__(self):
        self._resource_iters = PKDict(
            ips=ipaddress.IPv4Network(_cfg.ips).hosts(),
            ports=iter(range(_cfg.ports_min, _cfg.ports_max)),
            public_ports=iter(range(_cfg.public_ports_min, _cfg.public_ports_max)),
        )

    # TODO(e-carlin): Need to handle returning of freed resources (ex
    # when agent is terminated).
    def get_resources(self, resources_desired):
        res = PKDict()
        for k, v in resources_desired.items():
            res[k] = list(map(lambda _: next(self._resource_iters[k]), range(v)))
        return res


def for_simulation(sim_type, sid, uid=None, for_gui=True):
    if _in_agent():
        r = sirepo.agent_supervisor_api.request(
            "post",
            _cfg.server_uri,
            _cfg.server_token,
            json=PKDict(simulationType=sim_type, simulationId=sid),
        )
        r.raise_for_status()
        return PKDict(r.json())
    assert uid, f"Need to specify uid={uid} outside of agent"
    return (
        sirepo.util.import_submodule("global_resources", sim_type)
        .Allocator(
            _manager=_MANAGER,
            # SECURITY: uid must always be supplied by our systems. If
            # a bad actor was able to supply uid they could get resources
            # for any user by guessing uid, sim_type, and sid
            # correctly.
            _uid=uid,
            _sim_type=sim_type,
            _sid=sid,
        )
        .get(for_gui)
    )


def _in_agent():
    return _cfg.server_uri is not None


def _init():
    global _MANAGER, _cfg
    if _MANAGER:
        return
    _cfg = pkconfig.init(
        ips=("127.2.0.0/16", str, "cidr range of available ip addresses"),
        ports_max=(12200, int, "end of range of private ports (exclusive)"),
        ports_min=(12100, int, "start of range of private ports"),
        public_ports_max=(12100, int, "end of range for public ports (exclusive)"),
        public_ports_min=(12000, int, "start of range for public ports"),
        server_token=(None, str, "credential for api"),
        server_uri=(None, str, "how to connect to api"),
    )
    _MANAGER = _Manager()


_init()
