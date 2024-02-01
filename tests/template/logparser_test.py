# -*- coding: utf-8 -*-
"""PyTest for `sirepo.template.template_common.LogParser`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc


def test_activait_logparser():
    from pykern import pkunit
    from sirepo.template import activait

    pkunit.pkeq(
        "Descriptors cannot be created directly.\n",
        activait._parse_activate_log(pkunit.data_dir(), log_filename="activait1.txt"),
    )


def test_epicsllrf_logparser():
    from pykern import pkunit
    from sirepo.template import epicsllrf

    pkunit.pkeq(
        "a test EpicsDisconnectError\n",
        epicsllrf._parse_epics_log(pkunit.data_dir(), log_filename="epicsllrf1.txt"),
    )
    pkunit.pkeq(
        "",
        epicsllrf._parse_epics_log(pkunit.data_dir(), log_filename="unknown_case.txt"),
    )


def test_cloudmc_logparser():
    from pykern import pkunit
    from sirepo.template import cloudmc

    pkunit.pkeq(
        "No fission sites banked on MPI rank 0\n",
        cloudmc._parse_cloudmc_log(pkunit.data_dir(), log_filename="cloudmc1.txt"),
    )
    pkunit.pkeq(
        "An unknown error occurred, check CloudMC log for details",
        cloudmc._parse_cloudmc_log(pkunit.data_dir(), log_filename="unknown_case.txt"),
    )


def test_madx_logparser():
    from pykern import pkunit
    from sirepo.template import madx

    pkunit.pkeq(
        "Error: Test error\n\n",
        madx._MadxLogParser(
            pkunit.data_dir(), log_filename="madx1.txt"
        ).parse_for_errors(),
    )


def test_opal_logparser():
    from pykern import pkunit
    from sirepo.template import opal

    d = pkunit.data_dir()
    e = '"NPART" must be set.\n'
    pkunit.pkeq(
        e,
        opal._OpalLogParser(d, log_filename=f"opal1.txt").parse_for_errors(),
    )
    pkunit.pkeq(
        e,
        opal._OpalLogParser(d, log_filename=f"opal2.txt").parse_for_errors(),
    )
    pkunit.pkeq(
        """The z-momentum of the particle distribution
1958.907713
is different from the momentum given in the "BEAM" command
0.000000.
When using a "FROMFILE" type distribution
>     The z-momentum of the particle distribution
the momentum in the "BEAM" command should be
the same as the momentum of the particles in the file.
}>     When using a "FROMFILE" type distribution\n""",
        opal._OpalLogParser(d, log_filename=f"opal3.txt").parse_for_errors(),
    )
    pkunit.pkeq(
        """OpalWake::initWakefunction for element D2#0
"DISTRIBUTION" must be set in "RUN" command.\n""",
        opal._OpalLogParser(d, log_filename=f"opal4.txt").parse_for_errors(),
    )


def test_shadow_logparser():
    from pykern import pkunit
    from sirepo.template import shadow

    pkunit.pkeq(
        "Compound is not a valid chemical formula and is not present in the NIST compound database\n",
        shadow._parse_shadow_log(pkunit.data_dir(), log_filename="shadow1.txt"),
    )


def test_silas_logparser():
    from pykern import pkunit
    from sirepo.template import silas

    pkunit.pkeq(
        "Point evaulated outside of mesh boundary. Consider increasing Mesh Density or Boundary Tolerance.",
        silas._SilasLogParser(
            pkunit.data_dir(),
            log_filename="silas1.txt",
        ).parse_for_errors(),
    )
    pkunit.pkeq(
        "An unknown error occurred",
        silas._SilasLogParser(
            pkunit.data_dir(),
            log_filename="unknown_case.txt",
        ).parse_for_errors(),
    )


def test_srw_logparser():
    from pykern import pkunit
    from sirepo.template import template_common

    d = pkunit.data_dir()
    pkunit.pkeq(
        "An unknown error occurred",
        template_common.LogParser(d, log_filename=f"srw1.txt").parse_for_errors(),
    )
    pkunit.pkeq(
        "SRW can not compute this case. Longitudinal position of the Observation Plane is within the Integration limits.\n",
        template_common.LogParser(d, log_filename=f"srw2.txt").parse_for_errors(),
    )


def test_zgoubi_logparser():
    from pykern import pkunit
    from sirepo.template import zgoubi

    pkunit.pkeq("", zgoubi._parse_zgoubi_log(pkunit.data_dir(), "unknown_case.txt"))
    pkunit.pkeq(
        "example fortran runtime error\n",
        zgoubi._parse_zgoubi_log(pkunit.data_dir(), "zgoubi1.txt"),
    )
