import tensorflow as tf
from keras import backend as K


def HelloWorld():
    print('Hello World')


class VAE_Dense_Encoder(tf.keras.Model):
    def __init__(self, encoder_struc, act):
        l = len(encoder_struc) - 1
        self.inp = x = tf.keras.Input(shape=(encoder_struc[0],))

        for i in range(1, l):
            x = tf.keras.layers.Dense(encoder_struc[i], activation=act)(x)

        mu = tf.keras.layers.Dense(encoder_struc[l], name="mu")(x)
        sig = tf.keras.layers.Dense(encoder_struc[l], name="log_sig")(x)

        z = tf.keras.layers.Lambda(lambda a: a[0] + K.exp(a[1]) * K.random_normal(
            shape=(K.shape(a[0])[0], encoder_struc[l]), mean=0., stddev=1))([mu, sig])

        super(VAE_Dense_Encoder, self).__init__(self.inp, [mu, sig, z], name="Encoder")
        self.summary()


class Bernoulli_Dense_Decoder(tf.keras.Model):
    def __init__(self, decoder_struc, act):
        l = len(decoder_struc) - 1
        self.inp = x = tf.keras.Input(shape=(decoder_struc[0],))

        for i in range(1, l):
            x = tf.keras.layers.Dense(decoder_struc[i], activation=act)(x)

        outp = tf.keras.layers.Dense(decoder_struc[l], activation="sigmoid")(x)
        super(Bernoulli_Dense_Decoder, self).__init__(self.inp, outp, name="Decoder")
        self.summary()
