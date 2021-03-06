import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from skimage import draw
from keras import backend as K
from math import pi

try:
    import SDE_Tools
    import AE_Tools
    import SDE_VAE_Tools
except:
    raise Exception('Could not load necessary Tools. Please execute file in its original location.')


# Diesen Block einkommentieren, falls man Python auf der gpu laufen lässt

# Needed for gpu support on some machines
config = tf.compat.v1.ConfigProto(
    gpu_options=tf.compat.v1.GPUOptions(per_process_gpu_memory_fraction=0.95))
config.gpu_options.allow_growth = True
session = tf.compat.v1.Session(config=config)
tf.compat.v1.keras.backend.set_session(session)


########################################################
# Hyperparameter

# Hier bitte Pfad (absolut) angeben wo die Datensätze gespeichert werden sollen
# Ordner muss existieren, da Python auf vielen Systemen keine Ordner erstellen darf
#Bsp: data_path = 'C:/Users/[Name]/Desktop/Datasets/'
data_path = 'C:/Users/bende/Documents/Uni/Datasets/'

latent_dim = 1  # Dimension des latenten Raums (d)
frames = 50  # Anzahl der Frames im Datensatz (m+1)
M = 2  # Ordnung der SDEs
N = 1  # Anzahl der frames, über die gemittelt wird um Ableitungen zu approzimieren
# Achtung: die letzten (M-1)*N frames können nicht zum trainieren verwendet werden
# Je chaotischer die Daten, desto größer N und kleiner M>1

# gibt an ob die Daten geglättet rekonstruiert werden sollen, oder ob man mit Brownschen Bewegungen neue Daten generieren will
reconstructWithBM = False
# gibt an ob wie beim ODE-2-VAE die Form einer ODE M-ten Ordnung erzwungen werden soll oder nicht
forceHigherOrder = False
# Faktor um die Komplexität der Netzwerke, welche die SDE lernen, zu bestimmen.
SDE_Net_complexity = 20
# [SDE_Net_complexity] sollte proportional zur latenten Dimension gewählt werden.


VAE_epochs_starting = 3  # Anzahl der Epochen beim vor-Training der En-&Decoder
SDE_epochs_starting = 5 # Anzahl der Epochen beim vor-Training der SDE-Netzwerke (geht viel schneller)
#Combined_epochs = 10  # Anzahl der Epochen beim Training zusamman [Optional]
batch_size = 50
train_size = 3000  # <3000
test_size = 100  # <1000
act_CNN = 'relu'  # Aktivierungsfunktion für En-&Decoder
act_ms_Net = 'tanh'  # Aktivierungsfunktion für SDE-Netzwerke


# wenn diese parameter verändert werden, müssen die Datensätze neu erstellt werden

Time = 50  # SDEs werden besser gelernt, wenn [Time] ungefähr gleich [frames] ist.
# Frames, die beim erstellen des Datensatzes simuliert werden. Das Programm sieht davon nur [frames] viele.
simulated_frames = 200
simulated_Time = 3*pi  # Zeit, die beim erstellen des Datensatzes simuliert wird.
fps = Time/frames  # ist in der Theorie gleich 1/(Delta t)
n = 1  # Anzahl der Brownschen Bewegungen in der SDE
# Falls die SDEs zu sehr schwanken um gut gelernt zu werden, kann dieser Wert höher gestellt werden.
D_t = 1


# Bitte nicht ändern:
pictureWidth = 28
pictureHeight = 28
pictureColors = 1


################################################################################
# Datensatz laden oder erstellen

try:
    x_train = np.load(data_path+'SDE_Ball_train_{}frames.npy'.format(frames))
    x_test = np.load(data_path+'SDE_Ball_test_{}frames.npy'.format(frames))
    x_train_path = np.load(data_path+'SDE_Ball_train_path_{}frames.npy'.format(frames))
    x_test_path = np.load(data_path+'SDE_Ball_test_path_{}frames.npy'.format(frames))
    print('loaded datasets')
except:
    print('Dataset is being generated. This may take a few minutes.')

    X_0 = np.array([np.zeros(train_size), np.ones(train_size)])
    X_0 = np.transpose(X_0, [1, 0])

    # mu : R^d -> R^d , für d = latent_dim
    def mu(x):
        m = np.array([x[1], -x[0]])
        return m

    # sigma: R^d -> R^(dxn) , , für d = latent_dim
    def sigma(x):
        s = np.array([[0.2], [0.1]])
        #s = np.zeros((d,n))
        return s

    x_train_path = np.array(list(map(lambda i: SDE_Tools.ItoDiffusion(
        2, n, simulated_Time, frames, simulated_frames, X_0[i], mu, sigma), range(3000))))
    x_test_path = np.array(list(map(lambda i: SDE_Tools.ItoDiffusion(
        2, n, simulated_Time, frames, simulated_frames, X_0[i], mu, sigma), range(1000))))

    List = []
    for i in range(x_train_path.shape[0]):
        list = []
        for j in range(frames):
            position = [x_train_path[i, j, 0]/8+0.5, 0.5]
            radius = 0.12
            arr = np.zeros((28, 28))
            ro, co = draw.disk((position[0] * 28, position[1] *
                                28), radius=radius*28, shape=arr.shape)
            arr[ro, co] = 1
            list.append(arr)
        List.append(list)
    x_train = np.array(List)

    List = []
    for i in range(x_test_path.shape[0]):
        list = []
        for j in range(frames):
            position = [x_test_path[i, j, 0]/8+0.5, 0.5]
            radius = 0.12
            arr = np.zeros((28, 28))
            ro, co = draw.disk((position[0] * 28, position[1] *
                                28), radius=radius*28, shape=arr.shape)
            arr[ro, co] = 1
            list.append(arr)
        List.append(list)
    x_test = np.array(List)

    try:
        np.save(data_path+'SDE_Ball_train_path_{}frames'.format(frames), x_train_path)
        np.save(data_path+'SDE_Ball_test_path_{}frames'.format(frames), x_test_path)
        np.save(data_path+'SDE_Ball_train_{}frames'.format(frames), x_train)
        np.save(data_path+'SDE_Ball_test_{}frames'.format(frames), x_test)
        print('datasets saved for future use')
    except:
        print('could not save datasets')
    print('datasets generated')

x_train = x_train[0:train_size]
x_test = x_test[0:test_size]
x_train_path = x_train_path[0:train_size]
x_test_path = x_test_path[0:test_size]


# Dim: train_size x frames x pictureWidth x pictureHeight x pictureColors
x_train = np.transpose(np.array([x_train]), (1, 2, 3, 4, 0))


# Dim: test_size x frames x pictureWidth x pictureHeight x pictureColors
x_test = np.transpose(np.array([x_test]), (1, 2, 3, 4, 0))


########################################################
# Definitionen

#derivatives = SDE_Tools.make_tensorwise_average_derivatives(M, N, frames, fps)
derivatives = SDE_Tools.make_tensorwise_derivatives(M, frames, fps)

#encoder = AE_Tools.FramewiseEncoder(latent_dim, pictureWidth, pictureHeight, pictureColors, act_CNN, complexity=CNN_complexity, variational=True)
#decoder = AE_Tools.FramewiseDecoder(latent_dim, pictureWidth, pictureHeight, pictureColors, act_CNN, complexity=CNN_complexity)

encoder = AE_Tools.make_MNIST_encoder(latent_dim)
decoder = AE_Tools.make_MNIST_decoder(latent_dim)

ms_Net = SDE_Tools.mu_sig_Net(M, latent_dim, n, act_ms_Net,
                              SDE_Net_complexity, forceHigherOrder=forceHigherOrder)
reconstructor = SDE_Tools.Tensorwise_Reconstructor(
    latent_dim*pictureColors, n, Time, frames, ms_Net, D_t)


rec_loss = AE_Tools.make_binary_crossentropy_rec_loss(frames)
lr_loss = SDE_Tools.make_reconstruction_Loss(
    M, n, Time, frames, batch_size, reconstructor, derivatives)
p_loss = SDE_Tools.make_pointwise_Loss(M, latent_dim, Time, frames, ms_Net, D_t)
cv_loss = SDE_Tools.make_covariance_Loss(latent_dim, Time, frames, batch_size, ms_Net, D_t)
ss_loss = SDE_Tools.make_sigma_size_Loss(latent_dim, ms_Net)

MSE = tf.keras.losses.MeanSquaredError()


def SDELoss(Z_derivatives, ms_rec):
    S = 0
    S += 5*lr_loss(Z_derivatives, None)
    S += 10*p_loss(Z_derivatives, ms_rec)
    S += 1*cv_loss(Z_derivatives, ms_rec) #zuletzt 1
    return S


alpha = 0.2  # zuletzt 0.2


def StartingLoss(X_org, Z_enc_mean_List, Z_enc_log_var_List, Z_enc_List, Z_derivatives, Z_rec_List, X_rec_List):
    S = 20*rec_loss(X_org, X_rec_List)
    S += alpha*5*lr_loss(Z_derivatives, Z_rec_List)
    S += alpha*10*p_loss(Z_derivatives, None)
    S += alpha*1*cv_loss(Z_derivatives, None)
    return S

'''
#Falls man am Ende nochmal En-&Decoder zusammen mit dem SDE-Netz trainieren will
beta = 1
def FullLoss(X_org, Z_enc_mean_List, Z_enc_log_var_List, Z_enc_List, Z_derivatives, Z_rec_List, X_rec_List):
    S = 20*rec_loss(X_org, X_rec_List)
    S += beta*1*lr_loss(Z_derivatives, Z_rec_List)
    S += beta*10*p_loss(Z_derivatives, None)
    S += beta*1*cv_loss(Z_derivatives, None)
    return S
'''


########################################################
# SDE_VAE definieren

SDE_VAE = SDE_VAE_Tools.SDE_Variational_Autoencoder(
    M, N, encoder, derivatives, reconstructor, decoder, StartingLoss)
# inp hat dim: None x frames x pictureWidth x pictureHeight x pictureColors

print('model defined')


########################################################
# Model ohne SDE-Rekonstruktion die latenten Darstellungen lernen lassen
print('initial training for encoder and decoder to learn a latent representation')
SDE_VAE.apply_reconstructor = False
SDE_VAE.compile(optimizer='adam', loss=lambda x, arg: arg)
SDE_VAE.fit(x_train, x_train, epochs=VAE_epochs_starting, batch_size=batch_size, shuffle=False)
SDE_VAE.summary()

'''
# Latente Darstellung zum testen abspeichern
_, _, Z_enc_List, _, _, _ = SDE_VAE.fullcall(x_train)
np.save(data_path+'TestIfEncoderWorks2', Z_enc_List)
'''

########################################################
# Die SDE-Rekonstruktion der latenten Darstellungen lernen lassen
# Dieses training ist merklich schneller auf der haupt-cpu ohne verwendung einer gpu
print('training to learn SDE governing latent representation')

new_ms_Net = SDE_Tools.mu_sig_Net(M, latent_dim, n, act_ms_Net, SDE_Net_complexity, forceHigherOrder=forceHigherOrder)
new_ms_Net.compile(optimizer='adam', loss=SDELoss, metrics=[
               ss_loss, lambda x, m: lr_loss(x, None)])
reconstructor.ms_Net = new_ms_Net

with tf.device('/cpu:0'):
    _, _, Z_enc, _, _, _ = SDE_VAE.fullcall(x_train)
    z_train_derivatives = tf.constant(derivatives(Z_enc))
    new_ms_Net.fit(z_train_derivatives, z_train_derivatives,
               epochs=SDE_epochs_starting, batch_size=batch_size, shuffle=False)
    new_ms_Net.summary()


'''
########################################################
# En-&Decoder und SDE-Rekonstruktion zusammen trainieren
# Optional. Machmal sind Reconstructionen dann schöner.
print('main training with SDEs and Decoders combined')

SDE_VAE.custom_loss = FullLoss
SDE_VAE.compile(optimizer='adam', loss=lambda x, arg: arg)
SDE_VAE.fit(x_train, x_train, epochs=Combined_epochs, batch_size=batch_size, shuffle=False)
SDE_VAE.summary()
'''

########################################################
# Modell so einstellen, dass glatter reconstruiert wird.
SDE_VAE.apply_reconstructor = True
reconstructor.applyBM = reconstructWithBM


########################################################
# Ergebnisse speichern
Z_enc_mean_List, Z_enc_log_var_List, Z_enc_List, Z_derivatives, Z_rec_List, X_rec_List = SDE_VAE.fullcall(
    x_test)

np.save(data_path+'Results_SDE_Ball_Z_org_{}frames'.format(frames), x_test_path)
np.save(data_path+'Results_SDE_Ball_X_org_{}frames'.format(frames), x_test)
np.save(data_path+'Results_SDE_Ball_Z_enc_{}frames'.format(frames), Z_enc_List)
np.save(data_path+'Results_SDE_Ball_Z_rec_{}frames'.format(frames), Z_rec_List)
np.save(data_path+'Results_SDE_Ball_X_rec_{}frames'.format(frames), X_rec_List)

reconstructor.applyBM = True
_,_,_,_,Z_rec_BM,_ = SDE_VAE.fullcall(x_test)
np.save(data_path+'Results_SDE_Ball_Z_recBM_{}frames'.format(frames), Z_rec_BM)

########################################################
# Ergebnisse darstellen

_, _, enc_lat, _, rec_lat, rec_imgs = SDE_VAE.fullcall(x_test)

#print('enc_lat:', enc_lat.shape)
#print('rec_lat:', rec_lat.shape)

fig, axs = plt.subplots(9, 10)
for i in range(4):
    for j in range(10):
        axs[2*i, j].imshow(x_test[i, j, :, :, 0], cmap='gray')
        axs[2*i+1, j].imshow(rec_imgs[i, j, :, :, 0], cmap='gray')
for i in range(5):
    axs[8, 2*i].plot(np.linspace(1, frames, frames), enc_lat[i, :, 0], '-')
    axs[8, 2*i+1].plot(np.linspace(1, frames, frames), rec_lat[i, :, 0], '-')
plt.show()
