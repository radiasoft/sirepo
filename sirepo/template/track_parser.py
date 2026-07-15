"""TRACK parser and OPAL conversion.

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern import pkio
from pykern.pkcollections import PKDict
from pykern.pkdebug import pkdc, pkdlog, pkdp
from sirepo.template.lattice import LatticeUtil
from sirepo.template.line_parser import LineParser
import h5py
import math
import numpy
import pykern.pkjson
import re
import scipy.constants
import sirepo.sim_data
import sirepo.template.sdds_util
import sirepo.template.template_common
import struct


TRACK_CONVERSION_FILE = "track-conversion.py"

_COMPARISON_MAX_POINTS = 10000
_COMPARISON_PLOTS = PKDict(
    energy=PKDict(track_col=1, track_scale=1e6, opal_scale=1e6, label="energy [eV]"),
    emit_x=PKDict(
        track_col=10, track_scale=1e-5 / 4, opal_scale=1, label="x emittance [m]"
    ),
    emit_y=PKDict(
        track_col=13, track_scale=1e-5 / 4, opal_scale=1, label="y emittance [m]"
    ),
    rms_x=PKDict(track_col=3, track_scale=1e-2, opal_scale=1, label="x rms [m]"),
    rms_y=PKDict(track_col=4, track_scale=1e-2, opal_scale=1, label="y rms [m]"),
    rms_s=PKDict(opal_scale=1, label="z rms [m]"),
    s=PKDict(track_col=0, track_scale=1, opal_scale=1, label="s [m]"),
)
# beam.out columns (after dropping n_el, name): phi_rms[deg], btgm (beta*gamma)
_TRACK_PHI_RMS_COL = 7
_TRACK_BTGM_COL = 23

_BEAM_FREQUENCY_VAR = "beam_frequency_mhz"
_CM_MRAD_TO_M_RAD = 1e-5
_CM_TO_M = 1e-2
_GAUSS_TO_T = 1e-4
_SIM_TYPE_OPAL = "opal"
_SIM_DATA = sirepo.sim_data.get_class(_SIM_TYPE_OPAL)
_WATERBAG_FACTOR = 8.0
_WATERBAG_CUTOFF = round(math.sqrt(_WATERBAG_FACTOR), 9)

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
            models.elements.append(e)
        # TODO(pjm): use LatticeUtil for this
        models.elements = sorted(
            models.elements,
            key=lambda e: (e.type, e.name.lower()),
        )
        models.simulation.pkupdate(
            activeBeamlineId=bl.id,
            visualizationBeamlineId=bl.id,
            elementPosition="relative",
            name="TRACK Sim",
        )
        models.trackComparison.isTrackImport = "1"
        for n in ("plotAnimation", "plot2Animation"):
            models[n].includeLattice = "1"

    def _cav_element(self, n, params):
        d_elem, harm, te00 = float(params[0]), float(params[1]), float(params[2])
        return _SIM_DATA.model_defaults("RFCAVITY").pkupdate(
            fmapfn=f"eh_MWS.#{n:02d}",
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
            e = self._to_element(n, ele_type, t[2:])
            if e is None:
                continue
            elements.append((e, round(position, 6)))
            position += e.l
        return PKDict(elements=elements)

    def _sol3d_element(self, n, params):
        bf, d_elem, rap = float(params[0]), float(params[1]), float(params[2])
        return _SIM_DATA.model_defaults("SOLENOID").pkupdate(
            aperture=f"circle({rap * 2 * _CM_TO_M})",
            fmapfn=f"eh_EMS.#{n:02d}",
            ks=round(bf * _GAUSS_TO_T, 8),
            l=round(d_elem * _CM_TO_M, 6),
            name=self._new_name("SOL"),
            type="SOLENOID",
        )

    def _to_element(self, n, ele_type, params):
        if ele_type == "cav":
            return self._cav_element(n, params)
        if ele_type == "drift":
            return self._drift_element(params)
        if ele_type == "sol3d":
            return self._sol3d_element(n, params)
        pkdlog("unhandled TRACK element type={}", ele_type)
        return None


def beam_comparison(frame_args, sdds_filename):
    def _columns():
        if frame_args.quantity == "energy":
            return ["energy"]
        if frame_args.quantity == "emittance":
            return ["emit_x", "emit_y"]
        if frame_args.quantity == "rms":
            return ["rms_x", "rms_y"]
        if frame_args.quantity == "z":
            return ["rms_s"]
        raise AssertionError(f"unknown quantity={frame_args.quantity}")

    def _opal_points(col):
        v = sirepo.template.sdds_util.extract_sdds_column(sdds_filename, col, 0)[
            "values"
        ]
        step = int(round(len(v) / _COMPARISON_MAX_POINTS))
        if step > 0:
            v = v[0 : len(v) : step]
        return [p * _COMPARISON_PLOTS[col].opal_scale for p in v]

    def _plots(opal_x):
        d = _read_track_beam_out(frame_args)
        return [
            PKDict(
                x_points=_track_points(d, "s"),
                points=_track_points(d, s),
                label=f"TRACK {_COMPARISON_PLOTS[s].label}",
                style="scatter",
                circleRadius=4,
            )
            for s in _columns()
        ] + [
            PKDict(
                x_points=opal_x,
                points=_opal_points(s),
                label=f"OPAL {_COMPARISON_PLOTS[s].label}",
                style="scatter",
                circleRadius=1,
            )
            for s in _columns()
        ]

    def _track_points(beam_out, col):
        if col == "rms_s":
            return _track_z_rms(beam_out).tolist()
        return (
            beam_out[:, _COMPARISON_PLOTS[col].track_col]
            * _COMPARISON_PLOTS[col].track_scale
        ).tolist()

    def _track_z_rms(beam_out):
        # TRACKv37.pdf: phi_rms[deg] is the rms phase envelope of the beam
        # relative to the reference particle, at the RF frequency currently
        # in effect at that point in the lattice. Convert to an rms bunch
        # length [m], comparable to OPAL's rms_s, via
        # z = beta * lambda_rf * (phi_rms / 360).
        dist = beam_out[:, 0]
        phi_rms = beam_out[:, _TRACK_PHI_RMS_COL]
        btgm = beam_out[:, _TRACK_BTGM_COL]
        beta = btgm / numpy.sqrt(1 + btgm**2)
        positions, freqs = _rf_frequency_by_position(frame_args.sim_in)
        idx = numpy.clip(
            numpy.searchsorted(positions, dist, side="right") - 1,
            0,
            len(freqs) - 1,
        )
        lambda_rf = scipy.constants.c / freqs[idx]
        return beta * lambda_rf * (phi_rms / 360.0)

    x = _opal_points("s")
    r = sirepo.template.template_common.parameter_plot(
        x,
        _plots(x),
        frame_args,
        PKDict(
            y_label="",
            x_label="s [m]",
            dynamicYLabel=True,
        ),
    )
    n = int(len(r.plots) / 2)
    for i in range(n):
        r.plots[n + i].color = r.plots[i].color
    return r


def bunch_comparison(frame_args, h5_file):
    from sirepo.template import opal

    def _final_energy():
        d = _read_track_beam_out(frame_args)
        return d[-1][1]

    def _stats(coords):
        r = PKDict()
        # energy to W0, assuming proton
        amu_mev = scipy.constants.physical_constants[
            "proton mass energy equivalent in MeV"
        ][0]
        W0 = _final_energy()
        W = W0 + coords.dW
        gamma = 1.0 + W / amu_mev
        beta_gamma = numpy.sqrt(gamma**2 - 1.0)
        r.beta = beta_gamma / gamma
        xp = coords.xp_mrad * 1e-3
        yp = coords.yp_mrad * 1e-3
        r.tx = numpy.tan(xp)
        r.ty = numpy.tan(yp)
        r.pz = beta_gamma / numpy.sqrt(1.0 + r.tx**2 + r.ty**2)
        return r

    def _coord(name, coords):
        if name == "x":
            return coords.x_cm * 1e-2, "x [m]"
        if name == "y":
            return coords.y_cm * 1e-2, "y [m]"
        if name == "z":
            s = _stats(coords)
            return (
                -s.beta
                * scipy.constants.physical_constants["speed of light in vacuum"][0]
                * (coords.dt_ns * 1e-9)
            ), "z [m]"
        if name == "px":
            s = _stats(coords)
            return s.pz * s.tx, "px (#beta#gamma)"
        if name == "py":
            s = _stats(coords)
            return s.pz * s.ty, "py (#beta#gamma)"
        if name == "pz":
            s = _stats(coords)
            return s.pz, "pz (#beta#gamma)"
        if name == "q":
            return coords.iq, ""
        assert False

    def _get_range(field, p1, p2):
        return [
            min(min(p1[field]), min(p2[field])),
            max(max(p1[field]), max(p2[field])),
        ]

    def _points(file, frame_index, name):
        return numpy.array(file["/Step#{}/{}".format(frame_index, name)])

    def _read_coords(coord_file):
        # Nseed iq dt[ns] dW[MeV/u] x[cm] x'[mrad] y[cm] y'[mrad]
        d = numpy.loadtxt(coord_file, skiprows=1)
        return PKDict(
            iq=d[:, 1],
            dt_ns=d[:, 2],
            dW=d[:, 3],
            x_cm=d[:, 4],
            xp_mrad=d[:, 5],
            y_cm=d[:, 6],
            yp_mrad=d[:, 7],
        )

    def _read_opal():
        with h5py.File(str(frame_args.run_dir.join(h5_file)), "r") as f:
            return [
                _points(f, frame_args.frameIndex, frame_args.x),
                _points(f, frame_args.frameIndex, frame_args.y),
            ]

    def _read_track():
        d = _read_coords(
            _lib_file_abspath("trackComparison", "coordOut", frame_args.coordOut)
        )
        x, xlabel = _coord(frame_args.x, d)
        y, ylabel = _coord(frame_args.y, d)
        return [x, y], PKDict(x=xlabel, y=ylabel)

    p1 = _read_opal()
    p2, labels = _read_track()
    xrange = _get_range(0, p1, p2)
    yrange = _get_range(1, p1, p2)
    frame_args.pkupdate(
        plotRangeType="fixed",
        horizontalSize=xrange[1] - xrange[0],
        horizontalOffset=(xrange[0] + xrange[1]) / 2,
        verticalSize=yrange[1] - yrange[0],
        verticalOffset=(yrange[0] + yrange[1]) / 2,
    )

    b1 = opal.sim_frame_bunchAnimation(frame_args)
    if frame_args.frameReport == "bunchAnimation1":
        return b1.pkupdate(
            title="OPAL",
        )
    b2 = sirepo.template.template_common.heatmap(
        p2,
        frame_args,
        PKDict(
            x_label=labels.x,
            y_label=labels.y,
        ),
    )
    if frame_args.frameReport == "bunchAnimation2":
        return b2.pkupdate(
            title="TRACK",
        )
    if frame_args.frameReport == "bunchAnimation3":
        for i in range(len(b1.z_matrix)):
            for j in range(len(b1.z_matrix[0])):
                b1.z_matrix[i][j] -= b2.z_matrix[i][j]
        return b1.pkupdate(
            title="difference",
        )
    raise AssertionError(f"unknown comparison plot {frame_args.frameReport}")


def import_file(name, text, import_args):
    if name == "track.dat":
        return PKDict(
            importState="needLattice",
            eleData=_parse_track_file(text),
            latticeFileName="sclinac.dat",
        )
    if name == "sclinac.dat":
        return PKDict(
            importState="needLattice",
            eleData=_parse_sclinac_file(
                text,
                # optional track.dat info
                pykern.pkjson.load_any(import_args) if import_args else None,
            ),
            latticeFileName="fi_in.dat",
        )
    if name == "fi_in.dat":
        # must have already imported sclinac.dat
        if not import_args:
            raise IOError("Import a sclinac.dat first")
        return _parse_fi_in_file(text, pykern.pkjson.load_any(import_args))
    return None


def update_export(data, z, qcall):
    if _needs_track_conversion(data, qcall):
        z.writestr(
            TRACK_CONVERSION_FILE, _generate_track_conversion_file(data, qcall=qcall)
        )


def validate_file(file_type, path, sim_id, qcall):
    from sirepo import simulation_db

    def _hashed_name(name, ext="txt"):
        return f"{name}-{path.computehash()[:8]}.{ext}"

    n = None
    if "beamOut" in file_type or "coordOut" in file_type:
        n = _hashed_name(path.basename)
    elif m := re.search(r"/eh_(\w+\.\d+)$", str(path)):
        # imported TRACK input files are always eh_EMS.\d+ or eh_MWS.\d+
        n = _hashed_name(m.group(1))
        d = simulation_db.read_simulation_json(_SIM_TYPE_OPAL, sim_id, qcall)
        for e in d.models.elements:
            if e.get("fmapfn") and e.fmapfn.replace("#", "") == path.basename:
                e.fmapfn = n
        simulation_db.save_simulation_json(d, False, qcall=qcall)
    elif path.basename.lower() == "ini_dis.dat" and _is_track_ini_dis_file(path):
        n = _hashed_name("ini_dis", "dat")
    return PKDict(filename=n) if n else None


def write_parameters(data, run_dir, is_parallel):
    if _needs_track_conversion(data):
        pkio.write_text(
            run_dir.join(TRACK_CONVERSION_FILE),
            _generate_track_conversion_file(data),
        )


def _generate_track_conversion_file(data, qcall=None):
    from sirepo.template import opal

    def _conversions():
        cv = opal.code_var(data.models.rpnVariables)
        r = []
        seen = set()
        for e in data.models.elements:
            m = _using_track_fieldmap(e)
            if not m:
                continue
            lib_file = _SIM_DATA.lib_file_name_with_model_field(
                e.type, "fmapfn", e.fmapfn
            )
            if lib_file in seen:
                continue
            seen.add(lib_file)
            f = PKDict(type=m, lib_file=lib_file)
            if m == "MWS":
                f.pkupdate(frequency_mhz=cv.eval_var_with_assert(e.freq))
            r.append(f)
        d = LatticeUtil.find_first_command(data, "distribution")
        if _using_track_distribution(d, qcall=qcall):
            b = LatticeUtil.find_first_command(data, "beam")
            r.append(
                PKDict(
                    type="INIDIS",
                    lib_file=_SIM_DATA.lib_file_name_with_model_field(
                        "command_distribution", "fname", d.fname
                    ),
                    frequency_mhz=cv.eval_var_with_assert(b.bfreq),
                )
            )
        return r

    return sirepo.template.template_common.render_jinja(
        _SIM_TYPE_OPAL,
        PKDict(conversions=_conversions()),
        TRACK_CONVERSION_FILE,
    )


def _is_track_ini_dis_file(path):
    """Detect a TRACK ``ini_dis.dat`` binary particle distribution file.

    It's a Fortran sequential-unformatted file with a run-dependent header,
    so only check the expected 60-byte final record for framing.
    """
    with open(str(path), "rb") as f:
        f.seek(0, 2)
        if f.tell() < 68:
            return False
        f.seek(-68, 2)
        tail = f.read(68)
    prefix = struct.unpack_from("<i", tail, 0)[0]
    suffix = struct.unpack_from("<i", tail, 64)[0]
    return prefix == 60 and suffix == 60


def _lib_file_abspath(model_name, field, filename, qcall=None):
    return _SIM_DATA.lib_file_abspath(
        _SIM_DATA.lib_file_name_with_model_field(model_name, field, filename),
        qcall=qcall,
    )


def _needs_track_conversion(data, qcall=None):
    return any(
        _using_track_fieldmap(e) for e in data.models.elements
    ) or _using_track_distribution(
        LatticeUtil.find_first_command(data, "distribution"), qcall=qcall
    )


def _parse_fi_in_file(fi_in_text, data):
    p = [float(v) for v in fi_in_text.split()]
    for e in data.models.elements:
        if e.type == "RFCAVITY":
            e.lag = round(p.pop(0) * math.pi / 180.0, 8)
    return data


def _parse_sclinac_file(sclinac_text, data=None):
    from sirepo import simulation_db

    if not data:
        data = simulation_db.default_data(_SIM_TYPE_OPAL)
        data.models.rpnVariables = [
            PKDict(name=_BEAM_FREQUENCY_VAR, value=0),
        ]
    TRACKParser().parse_file(sclinac_text, data.models)
    if not data.models.beamlines or not data.models.beamlines[0]["items"]:
        raise AssertionError("No elements parsed from TRACK input")
    return data


def _parse_track_file(track_text):
    from sirepo import simulation_db

    # TODO(pjm): more sub methods, too many remaining conversion constants, common round()
    v = _parse_tran_namelist(track_text)
    m = (
        v.get("atp", 1.0)
        * scipy.constants.physical_constants["proton mass energy equivalent in MeV"][0]
        / 1e3
    )
    e = v.get("win", 0.0) * v.get("atp", 1.0) / 1e9 + m
    g = e / m
    b = math.sqrt(1.0 - 1.0 / g**2)

    def _transverse_sigmas(epsn, alfa, beta_t):
        r = epsn * _CM_MRAD_TO_M_RAD / _WATERBAG_FACTOR / (b * g)
        s = math.sqrt(beta_t * 1e-2 * r)
        p = math.sqrt((1.0 + alfa**2) / (beta_t * 1e-2) * r) * b * g
        c = -alfa / math.sqrt(1.0 + alfa**2) if alfa != 0 else 0.0
        return round(s, 9), round(p, 9), round(c, 9)

    f = v.get("freqb", 162.5e6)
    # epsnz in deg*%; betaz in deg/% — solve for sigma_phi and sigma_dw
    ez, az, bz = v.get("epsnz", 0.0), v.get("alfaz", 0.0), v.get("betaz", 0.0)
    sp = math.sqrt(ez * bz / _WATERBAG_FACTOR) if ez * bz > 0 else 0.0
    sw = math.sqrt(ez / bz / _WATERBAG_FACTOR) if ez * bz > 0 else 0.0
    sx, spx, cx = _transverse_sigmas(
        v.get("epsnx", 0.0), v.get("alfax", 0.0), v.get("betax", 1.0)
    )
    sy, spy, cy = _transverse_sigmas(
        v.get("epsny", 0.0), v.get("alfay", 0.0), v.get("betay", 1.0)
    )
    d = simulation_db.default_data(_SIM_TYPE_OPAL)
    LatticeUtil.find_first_command(d, "beam").pkupdate(
        particle="PROTON",
        mass=round(m, 9),
        charge=v.get("qq", 1.0),
        energy=round(e, 9),
        bcurrent=round(v.get("current", 0.0) * 1e-3, 9),
        bfreq=_BEAM_FREQUENCY_VAR,
        npart=int(v.get("npat", 0)),
    )
    if v.get("current", 0.0):
        LatticeUtil.find_first_command(d, "fieldsolver").pkupdate(fstype="FFT")
    LatticeUtil.find_first_command(d, "distribution").pkupdate(
        type="GAUSS",
        sigmax=sx,
        sigmay=sy,
        # sigma_phi [deg] -> z [m] via beta*lambda/(2*pi): sigmaz = sigma_phi/360 * beta*c/f
        sigmaz=round(sp / 360.0 * b * scipy.constants.c / f, 9),
        sigmapx=spx,
        sigmapy=spy,
        # beta*gamma * dp/p, where dp/p = (dW/W) * (gamma-1)/(gamma*beta^2)
        sigmapz=round(sw / 100.0 * (g - 1.0) / b, 9),
        corrx=cx,
        corry=cy,
        corrz=round(-az / math.sqrt(1.0 + az**2) if az != 0 else 0.0, 9),
        cutoffx=_WATERBAG_CUTOFF,
        cutoffy=_WATERBAG_CUTOFF,
        cutofflong=_WATERBAG_CUTOFF,
        cutoffpx=_WATERBAG_CUTOFF,
        cutoffpy=_WATERBAG_CUTOFF,
        cutoffpz=_WATERBAG_CUTOFF,
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


def _read_track_beam_out(frame_args):
    def _track_beam_out(filename):
        with open(filename, "r") as f:
            table = [line.strip().split() for line in f]
            return numpy.asarray(table[1::])[:, 2::].astype(float)

    return _track_beam_out(
        _lib_file_abspath("trackComparison", "beamOut", frame_args.beamOut)
    )


def _rf_frequency_by_position(sim_in):
    # Cavities along the beamline may run at different harmonics of the
    # fundamental (e.g. a multi-harmonic buncher, or later cavities running
    # at 2x/4x for a shorter wavelength), so TRACK's phi_rms[deg] is at the
    # RF frequency of whichever cavity the beam most recently passed through
    # (the fundamental frequency before the first cavity). Build a position
    # [m] -> frequency [Hz] step function from the beamline so beam.out rows
    # can be converted with the frequency that was actually in effect there.
    from sirepo.template import opal

    def _beam_frequency_hz(sim_in, code_var):
        # RFCAVITY elements may run at harmonics of the fundamental (freq = harm
        # * beam_frequency_mhz), so read the fundamental from the "beam" command
        # (bfreq) rather than an arbitrary cavity's freq expression.
        for c in sim_in.models.commands:
            if c._type == "beam":
                return code_var.eval_var_with_assert(c.bfreq) * 1e6
        raise AssertionError("no beam command found in sim_in")

    cv = opal.code_var(sim_in.models.rpnVariables)
    els_by_id = PKDict({e._id: e for e in sim_in.models.elements})
    pos = 0.0
    freq = _beam_frequency_hz(sim_in, cv)
    positions = [pos]
    freqs = [freq]
    for item_id in sim_in.models.beamlines[0]["items"]:
        e = els_by_id[item_id]
        pos += cv.eval_var_with_assert(e.get("l", 0))
        if e.type == "RFCAVITY":
            freq = cv.eval_var_with_assert(e.freq) * 1e6
        positions.append(pos)
        freqs.append(freq)
    return numpy.array(positions), numpy.array(freqs)


def _using_track_fieldmap(element):
    m = re.match(r"(EMS|MWS)\.\d+-.+\.txt$", element.get("fmapfn", ""))
    return m.group(1) if m else None


def _using_track_distribution(distribution, qcall=None):
    if not (
        distribution
        and distribution.get("type") == "FROMFILE"
        and distribution.get("fname")
    ):
        return False
    return _is_track_ini_dis_file(
        _lib_file_abspath(
            "command_distribution", "fname", distribution.fname, qcall=qcall
        )
    )
