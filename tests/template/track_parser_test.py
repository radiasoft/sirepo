"""Test for sirepo.template.track_parser

:copyright: Copyright (c) 2026 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""


def test_parse():
    from pykern import pkio, pkjson, pkunit
    from sirepo.template import track_parser

    d = pkunit.data_dir()
    m = track_parser.parse_fi_in_file(
        pkio.read_text(d.join("fi_in.dat")),
        track_parser.parse_sclinac_file(
            pkio.read_text(d.join("sclinac.dat")),
            track_parser.parse_track_file(pkio.read_text(d.join("track.dat"))),
        ),
    ).models
    m.simulation.pkdel("lastModified")
    with pkunit.save_chdir_work():
        pkjson.dump_pretty(m, filename="out.json")
        pkunit.file_eq("out.json", actual_path="out.json")
