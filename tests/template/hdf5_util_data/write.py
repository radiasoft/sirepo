import h5py
import sys
import time


def _write():
    with h5py.File(sys.argv[1], "w") as f:
        if len(sys.argv) > 2 and sys.argv[2] == "check_key":
            f.create_dataset("this_key_wont_exist_at_first", data=[])
        else:
            f.create_dataset("dataset_name", data=[])
            time.sleep(1)


_write()
