from sirepo.template.hdf5_util import HDF5Util
import sys


def _read():
    def _do(file_obj):
        if len(sys.argv) > 2 and sys.argv[2] == "check_key":
            file_obj["this_key_wont_exist_at_first"]

    HDF5Util(sys.argv[1]).read_while_writing(_do, timeout=1)


_read()
