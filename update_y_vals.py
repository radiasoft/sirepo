import h5py
import numpy

def bin(n):
    if n == 3:
        return numpy.uint8(2)
    return numpy.uint8(n)

with h5py.File("pets.h5", 'r+') as f:
    # print(f[mask])
    y = f["masks"]

    for i, image in enumerate(y):
        new = numpy.array(image)
        new[new > 2] = 2
        print(new)
        f["masks"][i] = new

with h5py.File("pets.h5", 'r') as f:
    # print(f[mask])
    y = f["masks"]
    for row in y[191]:
        print(row)