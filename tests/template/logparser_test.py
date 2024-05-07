"""PyTest for `sirepo.template.template_common.LogParser`

:copyright: Copyright (c) 2016 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from pykern.pkdebug import pkdc, pkdp, pkdlog, pkdexc


def test_activait_logparser():
    from sirepo.template import activait

    _case(
        "Descriptors cannot be created directly.\n",
        "activait1.txt",
        parser_function=activait._parse_activate_log,
    )


def test_epicsllrf_logparser():
    from sirepo.template import epicsllrf

    _case(
        "a test EpicsDisconnectError\n",
        "epicsllrf1.txt",
        parser_function=epicsllrf._parse_epics_log,
    )
    _case(
        "",
        "unknown_error_case.txt",
        parser_function=epicsllrf._parse_epics_log,
    )


def test_openmc_logparser():
    from sirepo.template import openmc

    _case(
        "No fission sites banked on MPI rank 0\n",
        "openmc1.txt",
        parser_function=openmc._parse_openmc_log,
    )
    _case(
        "An unknown error occurred, check OpenMC log for details",
        "unknown_error_case.txt",
        parser_function=openmc._parse_openmc_log,
    )


def test_madx_logparser():
    from sirepo.template import madx

    _case("Error: Test error\n\n", "madx1.txt", parser_object=madx._MadxLogParser)


def test_mpi_logparser():
    from sirepo.template import template_common

    _case(
        "Message from the error.",
        "mpi1.txt",
        parser_object=template_common._MPILogParser,
    )


def test_opal_logparser():
    from sirepo.template import opal

    _case('"NPART" must be set.\n', "opal1.txt", parser_object=opal._OpalLogParser)
    _case('"NPART" must be set.\n', "opal2.txt", parser_object=opal._OpalLogParser)
    _case(
        """The z-momentum of the particle distribution
1958.907713
is different from the momentum given in the "BEAM" command
0.000000.
When using a "FROMFILE" type distribution
>     The z-momentum of the particle distribution
the momentum in the "BEAM" command should be
the same as the momentum of the particles in the file.
}>     When using a "FROMFILE" type distribution\n""",
        "opal3.txt",
        parser_object=opal._OpalLogParser,
    )
    _case(
        """OpalWake::initWakefunction for element D2#0
"DISTRIBUTION" must be set in "RUN" command.\n""",
        "opal4.txt",
        parser_object=opal._OpalLogParser,
    )


def test_shadow_logparser():
    from sirepo.template import shadow

    _case(
        "Compound is not a valid chemical formula and is not present in the NIST compound database\n",
        "shadow1.txt",
        parser_function=shadow._parse_shadow_log,
    )


def test_silas_logparser():
    from sirepo.template import silas

    _case(
        "Point evaulated outside of mesh boundary. Consider increasing Mesh Density or Boundary Tolerance.",
        "silas1.txt",
        parser_object=silas._SilasLogParser,
    )
    _case(
        "An unknown error occurred",
        "unknown_error_case.txt",
        parser_object=silas._SilasLogParser,
    )


def test_srw_logparser():
    from sirepo.template import template_common

    _case(
        "An unknown error occurred", "srw1.txt", parser_object=template_common.LogParser
    )
    _case(
        "SRW can not compute this case. Longitudinal position of the Observation Plane is within the Integration limits.\n",
        "srw2.txt",
        parser_object=template_common.LogParser,
    )


def test_zgoubi_logparser():
    from sirepo.template import zgoubi

    _case("", "unknown_error_case.txt", parser_function=zgoubi._parse_zgoubi_log)
    _case(
        "example fortran runtime error\n",
        "zgoubi1.txt",
        parser_function=zgoubi._parse_zgoubi_log,
    )


def _case(expect, filename, parser_object=None, parser_function=None):
    from pykern import pkunit

    if parser_function:
        pkunit.pkeq(expect, parser_function(pkunit.data_dir(), log_filename=filename))
        return
    if parser_object:
        pkunit.pkeq(
            expect,
            parser_object(pkunit.data_dir(), log_filename=filename).parse_for_errors(),
        )
        return
    raise AssertionError("No parser provided for _case()")
