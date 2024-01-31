# -*- coding: utf-8 -*-
"""PyTest for `sirepo.template.template_common.LogParser`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""
from pykern import pkio
from pykern import pkunit
from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc
import pytest


def test_activait_logparser():
    from sirepo.template import activait

    pkunit.pkeq(
        activait._parse_activate_log(pkunit.data_dir(), log_filename="activait1.txt"),
        "Descriptors cannot be created directly.\n",
    )


def test_epicsllrf_logparser():
    from sirepo.template import epicsllrf

    pkunit.pkeq(
        epicsllrf._parse_epics_log(pkunit.data_dir(), log_filename="epicsllrf1.txt"),
        "a test EpicsDisconnectError\n",
    )
    pkunit.pkeq(
        epicsllrf._parse_epics_log(pkunit.data_dir(), log_filename="unknown_case.txt"),
        "",
    )


def test_cloudmc_logparser():
    from sirepo.template import cloudmc

    pkunit.pkeq(
        cloudmc._parse_cloudmc_log(pkunit.data_dir(), log_filename="cloudmc1.txt"),
        "No fission sites banked on MPI rank 0\n",
    )
    pkunit.pkeq(
        cloudmc._parse_cloudmc_log(pkunit.data_dir(), log_filename="unknown_case.txt"),
        "An unknown error occurred, check CloudMC log for details",
    )


def test_madx_logparser():
    pass


def test_opal_logparser():
    from sirepo.template import opal

    d = pkunit.data_dir()
    e = '"NPART" must be set.\n'
    pkunit.pkeq(
        opal._OpalLogParser(d, log_filename=f"opal1.txt").parse_for_errors(),
        e,
    )
    pkunit.pkeq(
        opal._OpalLogParser(d, log_filename=f"opal2.txt").parse_for_errors(),
        e,
    )
    pkunit.pkeq(
        opal._OpalLogParser(d, log_filename=f"opal3.txt").parse_for_errors(),
        """The z-momentum of the particle distribution
1958.907713
is different from the momentum given in the "BEAM" command
0.000000.
When using a "FROMFILE" type distribution
>     The z-momentum of the particle distribution
the momentum in the "BEAM" command should be
the same as the momentum of the particles in the file.
}>     When using a "FROMFILE" type distribution\n""",
    )
    pkunit.pkeq(
        opal._OpalLogParser(d, log_filename=f"opal4.txt").parse_for_errors(),
        """OpalWake::initWakefunction for element D2#0
"DISTRIBUTION" must be set in "RUN" command.\n"""
    )


def test_shadow_logparser():
    from sirepo.template import shadow

    pkunit.pkeq(
        shadow._parse_shadow_log(pkunit.data_dir(), log_filename="shadow1.txt"),
        "Compound is not a valid chemical formula and is not present in the NIST compound database\n"
    )


def test_silas_logparser():
    from sirepo.template import silas

    pkunit.pkeq(
        silas._SilasLogParser(
            pkunit.data_dir(),
            log_filename="silas1.txt",
        ).parse_for_errors(),
        "Point evaulated outside of mesh boundary. Consider increasing Mesh Density or Boundary Tolerance.",
    )
    pkunit.pkeq(
        silas._SilasLogParser(
            pkunit.data_dir(),
            log_filename="unknown_case.txt",
        ).parse_for_errors(),
        "An unknown error occurred",
    )


def test_srw_logparser():
    from sirepo.template import template_common

    d = pkunit.data_dir()
    pkunit.pkeq(
        template_common.LogParser(
            d, log_filename=f"srw1.txt"
        ).parse_for_errors(),
        "An unknown error occurred"
    )
    pkunit.pkeq(
        template_common.LogParser(
            d, log_filename=f"srw2.txt"
        ).parse_for_errors(),
        "SRW can not compute this case. Longitudinal position of the Observation Plane is within the Integration limits.\n"
    )


def test_zgoubi_logparser():
    pass
