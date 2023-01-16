import h5py
from PIL import ImageOps, Image
import numpy
import sys



def _read_file(run_dir, filename):
    res = numpy.load(run_dir + filename)
    if len(res.shape) == 1:
        res.shape = (res.shape[0], 1)
    return res

idx = int(sys.argv[1])
x = _read_file(
    'run/user/g6gCou4N/activait/OVpLXmeG/animation',
    '/predict.npy')
y =  _read_file(
    'run/user/g6gCou4N/activait/OVpLXmeG/animation',
    '/test.npy')
mask = numpy.argmax(x[idx], axis=-1)
mask = numpy.expand_dims(mask, axis=-1)


p = ImageOps.autocontrast(Image.fromarray(mask.reshape(64, 64).astype(numpy.uint8)))
p.save('maskpredict.png')
a = ImageOps.autocontrast(Image.fromarray(y[idx].astype(numpy.uint8)))
a.save('maskactual.png')
