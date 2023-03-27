
from keras.models import Model, Sequential
from keras.layers import Input, Dense, d, i, c, t, _, k, e, y, s, (, [, ', F, l, a, t, t, e, n, ', ,,  , ', D, e, n, s, e, ', ,,  , ', R, e, s, h, a, p, e, ', ], )
input_args = Input(shape=input_shape)
x = Flatten()(input_args)
x = Dense(2030, activation="relu")(x)
x = Reshape((35, 58))(x)
x = Dense(1024, activation="relu")(x)
x = Dense(1024, activation="relu")(x)
x = Dense(1024, activation="relu")(x)
x = Dense(1024, activation="relu")(x)
x = Dense(1024, activation="relu")(x)
x = Dense(1024, activation="relu")(x)
x = Dense(1024, activation="relu")(x)
x = Dense(58, activation="relu")(x)

model = Model(input_args, x)
model.save('unweighted.h5')
