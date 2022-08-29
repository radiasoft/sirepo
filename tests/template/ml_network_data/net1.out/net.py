
from keras.models import Model, Sequential
from keras.layers import Input, Dense, Add
input_args = Input(shape=(6,))
x = Dense(10, activation="relu")(input_args)
x_1 = Dense(10, activation="relu")(x)
x_3 = Dense(10, activation="relu")(x)
x_4 = Dense(10, activation="relu")(x)
x_5 = Dense(10, activation="relu")(x)
x_2 = Add()([x_3, x_4, x_5])
x = Add()([x_1, x_2])

x = Dense(1, activation="linear")(x)
model = Model(input_args, x)
