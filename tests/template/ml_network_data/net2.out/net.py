
from keras.models import Model, Sequential
from keras.layers import Input, Dense, Add
input_args = Input(shape=(6,))
x = Dense(10, activation="relu")(input_args)
x = Dense(10, activation="relu")(x)
x_2 = Dense(10, activation="relu")(x)
x_3 = Dense(10, activation="relu")(x)
x_1 = Add()([x_2, x_3])
x_5 = Dense(10, activation="relu")(x)
x_7 = Dense(10, activation="relu")(x)
x_8 = Dense(10, activation="relu")(x)
x_6 = Add()([x_7, x_8])
x_4 = Add()([x_5, x_6])
x_11 = Dense(10, activation="relu")(x)
x_12 = Dense(10, activation="relu")(x)
x_10 = Add()([x_11, x_12])
x_13 = Dense(10, activation="relu")(x)
x_9 = Add()([x_10, x_13])
x = Add()([x_1, x_4, x_9])
x = Dense(10, activation="relu")(x)

x = Dense(1, activation="linear")(x)
model = Model(input_args, x)
