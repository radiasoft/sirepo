import h5py
import sys
import time

def _write():
    with h5py.File(sys.argv[1], 'w') as f:
        time.sleep(3)
        f.create_dataset('dataset_name', data=[])
        time.sleep(3)

_write()