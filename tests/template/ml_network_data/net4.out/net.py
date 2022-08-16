
from keras.models import Model, Sequential
from keras.layers import Input, Dense, Concatenate
input_args = Input(shape=(6,))
x = Dense(10, activation="relu")(input_args)
x = Dense(10, activation="relu")(x)
x_1 = Dense(10, activation="relu")(x)
x_2 = Dense(10, activation="relu")(x_1)
x_3 = Dense(10, activation="relu")(x_2)
x_3 = Dense(10, activation="relu")(x_3)
x_2 = Concatenate()([x_3, x_2])
x_2 = Dense(10, activation="relu")(x_2)
x_2 = Dense(10, activation="relu")(x_2)
x_1 = Concatenate()([x_2, x_1])
x_1 = Dense(10, activation="relu")(x_1)
x = Concatenate()([x_1, x])
x = Dense(10, activation="relu")(x)

x = Dense(1, activation="linear")(x)
model = Model(input_args, x)
