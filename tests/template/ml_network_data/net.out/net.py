
from keras.models import Model, Sequential
from keras.layers import Input, Dense, Add
input_args = Input(shape=(6,))
x = Dense(10, activation="relu")(input_args)
x_2 = Dense(10, activation="relu")(x)
x_3 = Dense(10, activation="relu")(x)
x_4 = Dense(10, activation="relu")(x)
x_1 = Add()([x_2, x_3, x_4])
x_5 = Dense(10, activation="relu")(x)
x = Add()([x_1, x_5])

x = Dense(1, activation="linear")(x)
model = Model(input_args, x)
