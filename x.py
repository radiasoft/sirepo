import h5py
import numpy
# import pickle
import os
# from IPython.display import Image, display
from tensorflow.keras.preprocessing.image import load_img
# from PIL import ImageOps
import PIL.Image


# TODO (gurhar1133): need classes too?
input_dir = "images/"
target_dir = "annotations/trimaps/"
img_size = (160, 160)
num_classes = 3
batch_size = 32

input_img_paths = sorted(
    [
        os.path.join(input_dir, fname)
        for fname in os.listdir(input_dir)
        if fname.endswith(".jpg")
    ]
)
target_img_paths = sorted(
    [
        os.path.join(target_dir, fname)
        for fname in os.listdir(target_dir)
        if fname.endswith(".png") and not fname.startswith(".")
    ]
)
sample_count = len(input_img_paths)
print("Number of samples:", sample_count)


with h5py.File("pets.h5", 'w') as f:
    imgs = f.create_dataset(
        'images',
        (sample_count, 64, 64, 3),
        dtype=numpy.float64,
    )
    masks = f.create_dataset(
        'masks',
        (sample_count, 64, 64),
        dtype=numpy.uint8,
    )
#     insert images into the groups
    idx = 0
    for input_path, target_path in zip(input_img_paths, target_img_paths):
        imgs[idx] = load_img(input_path, target_size=(64, 64))
        masks[idx] = load_img(target_path, target_size=(64, 64), color_mode="grayscale")
        idx += 1



# for input_path, target_path in zip(input_img_paths, target_img_paths):
#     print(input_path, "|", target_path)



# # Display input image #7
# display(Image(filename=input_img_paths[9]))

# # Display auto-contrast version of corresponding target (per-pixel categories)
# img = ImageOps.autocontrast(load_img(target_img_paths[9]))
# display(img)



# def get_label_map(labels):
#     with open('batches.meta', 'rb') as f:
#         all_labels = pickle.load(f)['label_names']
#     return {
#         all_labels.index(v) : labels.index(v) for v in labels
#     }

# outfn = 'out.h5'

# labels = ['bird', 'cat', 'truck', 'frog']
# print('labels: {}'.format(labels))
# label_map = get_label_map(labels)

# count = 0

# data_filenames = ['data_batch_1', 'data_batch_2', 'data_batch_3', 'data_batch_4', 'data_batch_5', 'test_batch']

# for filename in data_filenames:
#     with open (filename, 'rb') as f:
#         r = pickle.load(f, encoding='bytes')
#         for lbl in r[b'labels']:
#             if lbl in label_map:
#                 count += 1

# print('count: {}'.format(count))

# with h5py.File(outfn, 'w') as f:
#     meta = f.create_group('metadata')
#     meta.create_dataset(
#         'labels',
#         (len(labels),),
#         'S10',
#         [v.encode('ascii', 'ignore') for v in labels],
#     )
#     imgs = f.create_dataset(
#         'images',
#         (count,32,32,3),
#         dtype=numpy.uint8,
#     )
#     img_types = meta.create_dataset(
#         'image_types',
#         (count,),
#         dtype=numpy.uint8,
#     )

#     curr = 0

#     for filename in data_filenames:
#         with open (filename, 'rb') as f:
#             r = pickle.load(f, encoding='bytes')
#             for idx, lbl in enumerate(r[b'labels']):
#                 if lbl in label_map:
#                     print('#{} lbl: {} mapped: {}'.format(idx, lbl, label_map[lbl]))
#                     img_types[curr] = label_map[lbl]
#                     imgs[curr] = r[b'data'][idx].reshape((3,32,32)).transpose(1,2,0)
#                     curr += 1
#                     if curr >= count:
#                         break


# import PIL.Image
# with h5py.File(outfn, 'r') as f:
#     print('images: {}'.format(f['images'].shape))
#     print('image_types: {}'.format(f['metadata/image_types'].shape))
#     idx = 4
#     img = PIL.Image.fromarray(f['images'][idx])
#     print('it is a {}: {}'.format(
#         f['metadata/image_types'][idx],
#         labels[f['metadata/image_types'][idx]],
#     ))
#     img.save('test2.png')

