from sirepo.template.hdf5_util import HDF5Util
import sys


def _read():
    with HDF5Util(sys.argv[1]).read_while_writing() as f:
        if len(sys.argv) > 2 and sys.argv[2] == "check_key":
                f["this_key_wont_exist_at_first"]


_read()
