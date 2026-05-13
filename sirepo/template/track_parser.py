"""TRACK parser.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo.template.line_parser import LineParser
import math
import re
import scipy.constants
import sirepo.sim_data
import sirepo.template.template_common


_CM_TO_M = 1e-2
_GAUSS_TO_T = 1e-4
_SIM_DATA = sirepo.sim_data.get_class("opal")
_BEAM_FREQUENCY_VAR = "beam_frequency_mhz"

# Elements that control simulation flow, not beamline geometry
_CONTROL_TYPES = frozenset(
    [
        "align",
        "cdump",
        "enge",
        "filtr",
        "matrx",
        "prmtr",
        "scrch",
        "stop",
        "swtch",
        "updat",
    ]
)


class TRACKParser:

    def parse_file(self, sclinac_text, models):
        self._counts = PKDict()
        self.parser = LineParser(100)
        r = self._parse_sclinac(sclinac_text)
        self._build_beamline(models, r)
        return sorted(set(r.files))

    def _build_beamline(self, models, r):
        bl = _SIM_DATA.model_defaults("beamline").pkupdate(
            id=self.parser.next_id(),
            items=[],
            name="BL1",
            positions=[],
        )
        models.beamlines.append(bl)
        for e, p in r.elements:
            e._id = self.parser.next_id()
            bl["items"].append(e._id)
            # TODO(pjm): don't need elemedge
            bl.positions.append(PKDict(elemedge=p))
            models.elements.append(e)
        # TODO(pjm): use LatticeUtil for this
        models.elements = sorted(
            models.elements,
            key=lambda e: (e.type, e.name.lower()),
        )
        models.simulation.activeBeamlineId = (
            models.simulation.visualizationBeamlineId
        ) = bl.id

    def _cav_element(self, n, params):
        d_elem, harm, te00 = float(params[0]), float(params[1]), float(params[2])
        return _SIM_DATA.model_defaults("RFCAVITY").pkupdate(
            aperture=f"circle(0.01)",
            # TODO(pjm): unique filenames
            fmapfn=f"mws{n:02d}.txt",
            freq=f"{harm} * {_BEAM_FREQUENCY_VAR}",
            l=round(d_elem * _CM_TO_M, 6),
            name=self._new_name("CAV"),
            type="RFCAVITY",
            volt=te00,
        )

    def _drift_element(self, params):
        d_elem, rapx, rapy = float(params[0]), float(params[1]), float(params[2])
        if rapy < 0:
            aperture = f"circle({abs(rapy) * 2 * _CM_TO_M})"
        else:
            aperture = f"rectangle({rapx * 2 * _CM_TO_M}, {rapy * 2 * _CM_TO_M})"
        return _SIM_DATA.model_defaults("DRIFT").pkupdate(
            aperture=aperture,
            l=round(d_elem * _CM_TO_M, 6),
            name=self._new_name("D"),
            type="DRIFT",
        )

    def _new_name(self, prefix):
        c = self._counts.get(prefix, 0) + 1
        self._counts[prefix] = c
        return f"{prefix}{c:03d}"

    def _parse_sclinac(self, sclinac_text):
        elements = []
        files = []
        position = 0.0
        for line in sclinac_text.split("\n"):
            v = line.strip()
            if not v or v[0] == "!" or re.match(r"^c\b", v):
                continue
            t = v.split()
            if len(t) < 2:
                continue
            n, ele_type = int(t[0]), t[1].lower()
            if ele_type in _CONTROL_TYPES:
                continue
            e = self._to_element(n, ele_type, t[2:], files)
            if e is None:
                continue
            elements.append((e, round(position, 6)))
            position += e.l
        return PKDict(elements=elements, files=files)

    def _sol3d_element(self, n, params, files):
        bf, d_elem, rap = float(params[0]), float(params[1]), float(params[2])
        files.append(f"eh_EMS.#{n:02d}")
        return _SIM_DATA.model_defaults("SOLENOID").pkupdate(
            aperture=f"circle({rap * 2 * _CM_TO_M})",
            fmapfn=f"ems{n:02d}_1d.txt",
            ks=round(bf * _GAUSS_TO_T, 8),
            l=round(d_elem * _CM_TO_M, 6),
            name=self._new_name("SOL"),
            type="SOLENOID",
        )

    def _to_element(self, n, ele_type, params, files):
        if ele_type == "cav":
            files.append(f"eh_MWS.#{n:02d}")
            return self._cav_element(n, params)
        if ele_type == "drift":
            return self._drift_element(params)
        if ele_type == "sol3d":
            return self._sol3d_element(n, params, files)
        pkdlog("unhandled TRACK element type={}", ele_type)
        return None


def parse_fi_in_file(fi_in_text, data):
    p = [float(v) for v in fi_in_text.split()]
    for e in data.models.elements:
        if e.type == "RFCAVITY":
            e.lag = round(p.pop(0) * math.pi / 180.0, 8)
    return data


def parse_sclinac_file(sclinac_text, data=None):
    from sirepo import simulation_db

    if not data:
        data = simulation_db.default_data("opal")
    files = TRACKParser().parse_file(sclinac_text, data.models)
    if not data.models.beamlines or not data.models.beamlines[0]["items"]:
        raise AssertionError("No elements parsed from TRACK input")
    return data, files


def parse_track_file(track_text):
    from sirepo import simulation_db

    def find_first_command(data, name):
        return [c for c in d.models.commands if c._type == name][0]

    v = _parse_tran_namelist(track_text)
    sd = sirepo.sim_data.get_class("opal")
    m = (
        v.get("atp", 1.0)
        * scipy.constants.physical_constants["proton mass energy equivalent in MeV"][0]
        / 1e3
    )
    e = v.get("win", 0.0) * v.get("atp", 1.0) / 1e9 + m
    g = e / m
    b = math.sqrt(1.0 - 1.0 / g**2)

    def _transverse_sigmas(epsn, alfa, beta_t):
        r = epsn * 1e-5 / 4.0 / (b * g)
        s = math.sqrt(beta_t * 1e-2 * r)
        p = math.sqrt((1.0 + alfa**2) / (beta_t * 1e-2) * r)
        c = -alfa / math.sqrt(1.0 + alfa**2) if alfa != 0 else 0.0
        return round(s, 9), round(p, 9), round(c, 9)

    f = v.get("freqb", 162.5e6)
    # epsnz in deg*%; betaz in deg/% — solve for sigma_phi and sigma_dw
    ez, az, bz = v.get("epsnz", 0.0), v.get("alfaz", 0.0), v.get("betaz", 0.0)
    sp = math.sqrt(ez * bz / 4.0) if ez * bz > 0 else 0.0
    sw = math.sqrt(ez / bz / 4.0) if ez * bz > 0 else 0.0
    sx, spx, cx = _transverse_sigmas(
        v.get("epsnx", 0.0), v.get("alfax", 0.0), v.get("betax", 1.0)
    )
    sy, spy, cy = _transverse_sigmas(
        v.get("epsny", 0.0), v.get("alfay", 0.0), v.get("betay", 1.0)
    )
    d = simulation_db.default_data("opal")
    find_first_command(d, "beam").pkupdate(
        particle="PROTON",
        mass=round(m, 9),
        charge=v.get("qq", 1.0),
        energy=round(e, 9),
        bcurrent=round(v.get("current", 0.0) * 1e-3, 9),
        bfreq=_BEAM_FREQUENCY_VAR,
        npart=int(v.get("npat", 0)),
    )
    find_first_command(d, "distribution").pkupdate(
        type="GAUSS",
        sigmax=sx,
        sigmay=sy,
        # sigma_phi [deg] -> z [m] via beta*lambda/(2*pi): sigmaz = sigma_phi/360 * beta*c/f
        sigmaz=round(sp / 360.0 * b * scipy.constants.c / f, 9),
        sigmapx=spx,
        sigmapy=spy,
        # dp/p from dW/W: dp/p = (dW/W) * (gamma-1)/(gamma*beta^2)
        sigmapz=round(sw / 100.0 * (g - 1.0) / (g * b**2), 9),
        corrx=cx,
        corry=cy,
        corrz=round(-az / math.sqrt(1.0 + az**2) if az != 0 else 0.0, 9),
        name="DIST1",
    )
    d.models.rpnVariables = [
        PKDict(name=_BEAM_FREQUENCY_VAR, value=round(f / 1e6, 6)),
    ]
    return d


def _parse_tran_namelist(text):
    # strip table_dir (Windows path with backslashes that f90nml can't parse)
    text = re.sub(r"(?im)^\s*table_dir\s*=.*$", "", text)
    v = sirepo.template.template_common.NamelistParser().parse_text(text)
    if "tran" not in v:
        raise AssertionError("No &TRAN...&END block found in track.dat")
    return v["tran"]
