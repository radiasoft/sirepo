
from keras.models import Model, Sequential
from keras.layers import Input, Dense, Activation, Conv2D, Add
input_args = Input(shape=input_shape)
x = Dense(10, activation="relu")(input_args)
x_1 = Activation("relu")(x)
x_1 = Conv2D(10,
    activation="relu",
    kernel_size=(3, 3),
    kernel_initializer=keras.initializers.RandomNormal(),
    strides=1,
    padding="same"
    )(x_1)
x_1 = Dense(10, activation="relu")(x_1)
x_2 = Conv2D(10,
    activation="relu",
    kernel_size=(3, 3),
    kernel_initializer=keras.initializers.RandomNormal(),
    strides=1,
    padding="same"
    )(x)
x = Add()([x_1, x_2])
x_3 = Activation("relu")(x)
x_3 = Conv2D(10,
    activation="relu",
    kernel_size=(3, 3),
    kernel_initializer=keras.initializers.RandomNormal(),
    strides=1,
    padding="same"
    )(x_3)
x_3 = Dense(10, activation="relu")(x_3)
x_4 = Conv2D(10,
    activation="relu",
    kernel_size=(3, 3),
    kernel_initializer=keras.initializers.RandomNormal(),
    strides=1,
    padding="same"
    )(x)
x = Add()([x_3, x_4])
x = Conv2D(10,
    activation="relu",
    kernel_size=(3, 3),
    kernel_initializer=keras.initializers.RandomNormal(),
    strides=1,
    padding="same"
    )(x)

x = Dense(output_shape, activation="linear")(x)
model = Model(input_args, x)
model.save('unweighted.h5')
