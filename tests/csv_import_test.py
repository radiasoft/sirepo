import sirepo.csv


def test_import():
    from pykern import pkunit, pkio
    from sirepo import csv

    for d in pkunit.case_dirs(group_prefix="conformance"):
        for f in pkio.sorted_glob("*.csv"):
            _ = sirepo.csv.read_as_number_list(f)
        pass

    for d in pkunit.case_dirs(group_prefix="deviance"):
        for f in pkio.sorted_glob("*.csv"):
            with pkunit.pkexcept("invalid file"):
                _ = sirepo.csv.read_as_number_list(f)
