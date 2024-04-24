from sirepo.template.hdf5_util import HDF5Util
import sys


def _read():
    with HDF5Util(sys.argv[1]).read_while_writing() as f:
        print("trying to read", f)
    print("Read complete")

_read()
