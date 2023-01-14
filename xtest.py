import h5py
from PIL import ImageOps, Image
import numpy
from tensorflow.keras.preprocessing.image import load_img

with h5py.File("pets.h5", 'r') as f:
    print("h5 mask shape", f['masks'].shape)
    print("COMP", type(f['masks'][100][0][0]), f['masks'][100].shape, f['masks'][100])

#     print('images: {}'.format(f['images'].shape))
#     print('masks: {}'.format(f['masks'].shape))
#     idx = 100
#     print('image: ', f['images'][idx])
#     print('mask: ', f['masks'][idx])
#     img = Image.fromarray(f['images'][idx])
#     img.save('img.png')
#     mask = ImageOps.autocontrast(Image.fromarray(f['masks'][idx]))
#     mask.save('mask.png')


def _read_file(run_dir, filename):
    res = numpy.load(run_dir + filename)
    if len(res.shape) == 1:
        res.shape = (res.shape[0], 1)
    return res
idx = 600
x = _read_file(
    'run/user/g6gCou4N/activait/OVpLXmeG/animation',
    '/predict.npy')
y =  _read_file(
    'run/user/g6gCou4N/activait/OVpLXmeG/animation',
    '/test.npy')
# print(len(x))
# print(len(y))
# print("COMP  y[0]", type(y[0][0][0]), y[0].shape, y[0])
print("x[0]", x[0])
print("x[0].shape", x[0][0].shape)
print("y[0].shape", y[0].shape)
# print("pred", x[0].reshape(64, 64).astype(numpy.uint8))
mask = numpy.argmax(x[idx], axis=-1)
mask = numpy.expand_dims(mask, axis=-1)
# print(mask)

print(mask)
p = ImageOps.autocontrast(Image.fromarray(mask.reshape(64, 64).astype(numpy.uint8)))
p.save('maskpredict.png')
print(y[100] == mask)
a = ImageOps.autocontrast(Image.fromarray(y[idx].astype(numpy.uint8)))
a.save('maskactual.png')

# x = _read_file(frame_args.run_dir, _OUTPUT_FILE.predictFile)[:, idx]