from mpl_toolkits.axes_grid1 import ImageGrid
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation
from scipy.optimize import fsolve
from skimage import draw
import tensorflow as tf
import time
# %%

# drag = Strömungswiderstand * Druck / 2
def time_step(step_size, position, velocity, radius, object_number, gravity=120, drag=0.1):
    position += step_size * velocity

    collision_matrix = np.array([np.linalg.norm(position[i] - position[j]) < radius[i] + radius[j]
                                 for i in range(object_number) for j in range(object_number)]).reshape(object_number, object_number)
    for i in range(object_number):
        for j in range(object_number):
            if (j < i) and collision_matrix[i, j] == True:
                # Berechnet neue Velosity der Bälle, falls es eine Kollision gab
                m1, m2 = radius[i] ** 2, radius[j] ** 2
                x1, x2 = position[i], position[j]
                d = np.linalg.norm(x1 - x2) ** 2
                v1, v2 = velocity[i], velocity[j]

                u1 = v1 - 2 * m2 / (m1 + m2) * np.dot(v1 - v2, x1 - x2) / d * (x1 - x2)
                u2 = v2 - 2 * m1 / (m1 + m2) * np.dot(v2 - v1, x2 - x1) / d * (x2 - x1)

                # Berechnet die Strecke die die Bälle seit der Kollision zurückgelegt haben, kann in seltenen Fällen dazu führen,
                # dass Bälle für ein Frame ineinander geraten.

                def F(r):
                    return np.linalg.norm(x1 - x2 + r * (u1 - u2)) - (radius[i] + radius[j])
                t = fsolve(F, 1)[0]
                velocity[i] = u1
                velocity[j] = u2

                if t > 0 and t < 0.1:
                    position[i] += 2 * t * u1
                    position[j] += 2 * t * u2

    # Kollisionen mit den Wänden modellieren:
    a = position[:, 0] - radius < 0
    b = position[:, 0] + radius > 1
    c = position[:, 1] - radius < 0
    d = position[:, 1] + radius > 1
    if True in a:
        velocity[a, 0] = - velocity[a, 0]
        position[a, 0] = radius[a]
    if True in b:
        velocity[b, 0] = - velocity[b, 0]
        position[b, 0] = 1 - radius[b]
    if True in c:
        velocity[c, 1] = - velocity[c, 1]
        position[c, 1] = radius[c]
    if True in d:
        velocity[d, 1] = - velocity[d, 1]
        position[d, 1] = 1 - radius[d]

    #print(velocity)
    #print(radius)

    velocity[:, 0] += (radius ** 2) * gravity * step_size
    #print(np.tile(1 - (velocity ** 2).sum(axis=1) * drag / radius * step_size, (2, 1)).transpose())
    velocity *= np.tile(1 - (velocity ** 2).sum(axis=1) * drag / radius * step_size, (2, 1)).transpose()

    return position, velocity


def create_dataset(dataset_size, frames, picture_size, object_number, variation):
    dataset = []
    step_size = 0.007
    steps = frames * 30

    for j in range(dataset_size):

        sequence = []
        if variation == True:
            radius = [np.random.uniform(0.06, 0.15)]
            velocity = [np.random.uniform(-1, 1, size=2)]
        else:
            radius = [0.12]
            alpha = np.random.uniform(0, 1)
            velocity = [[np.cos(alpha) * 0.8, np.sin(alpha) * 0.8]]
        position = [np.random.uniform(0 + radius[0], 1 - radius[0], size=2)]
        for i in range(object_number - 1):
            counter = 0
            restart = True
            while restart:

                if variation == True:
                    start_radius = np.random.uniform(0.05, 0.15)
                    start_velocity = np.random.uniform(-1, 1, size=2)
                else:
                    start_radius = 0.12
                    alpha = np.random.uniform(0, 1)
                    start_velocity = [np.cos(alpha) * 0.8, np.sin(alpha) * 0.8]
                start_position = np.random.uniform(0 + start_radius, 1 - start_radius, size=2)
                collisions = np.linalg.norm(start_position - np.array(position),
                                            axis=1) < np.array(radius) + start_radius
                counter += 1
                if sum(collisions) == 0:
                    restart = False
                    break
                if counter == 200:
                    restart = False
                    break
            if counter == 200:
                print('Mit diesen Konfigurationen wurden keine passenden Startbedingungen gefunden')
                break
            else:
                radius.append(start_radius)
                position.append(start_position)
                velocity.append(start_velocity)

        radius = np.array(radius)
        position = np.array(position)
        velocity = np.array(velocity)

        for i in range(steps):
            position, velocity = time_step(step_size, position, velocity, radius, object_number)
            if i % 15 == 0:
                arr = np.zeros((picture_size, picture_size))
                for i in range(object_number):
                    ro, co = draw.disk((position[i, 0] * picture_size, position[i, 1] *
                                        picture_size), radius=radius[i]*picture_size, shape=arr.shape)
                    arr[ro, co] = 1
                sequence.append(arr)
        sequence = np.array(sequence)
        dataset.append(sequence)
    dataset = np.array(dataset)
    dataset = np.transpose(dataset, (0, 2, 3, 1))
    return dataset


class DataGenerator(tf.keras.utils.Sequence):
    def __init__(self, object_number, picture_size, frames, dataset_size, batch_size, variation):
        self.object_number = object_number
        self.picture_size = picture_size
        self.frames = frames
        self.dataset_size = dataset_size
        self.batch_size = batch_size
        self.variation = variation

    def __len__(self):
        return int(self.dataset_size / self.batch_size)

    def __getitem__(self, index):
        X = create_dataset(self.batch_size, self.frames, self.picture_size,
                           self.object_number, self.variation)
        return X


video = create_dataset(1, 10, 200, 3, False)  # evtl. step size verringern!
for i in range(10):
    plt.axis('off')
    plt.imshow(video[0, :, :, i], cmap='gray')
    plt.pause(0.2)
    plt.clf()
plt.show()


#tic = time.perf_counter()
#x_train = create_dataset(100, 10, 28, 3, False)
#toc = time.perf_counter()
#print(f"Datensatz erstellen braucht {toc - tic:0.4f} Sekunden")
#x_test = create_dataset(100, 10, 28, 3, False)

# for j in range(len(x_test)):
#    for i in np.random.choice(range(3, 10), 3, replace=False):
#        x_test[j, :, :, i] = np.zeros((28, 28))

#k = 0
#fig, index = plt.figure(figsize=(10, 10)), np.random.randint(len(x_test), size=5)
#grid = ImageGrid(fig, 111,  nrows_ncols=(10, 10), axes_pad=0.1,)
#plot = [x_test[index[0]][:, :, j] for j in range(10)]
# for i in index:
#    if k != 0:
#        original = [x_test[i][:, :, j] for j in range(10)]
#        plot = np.vstack((plot, original))
#    reconst = [x_train[i][:, :, j] for j in range(10)]
#    plot = np.vstack((plot, reconst))
#    k += 1
# for ax, im in zip(grid, plot):
#    plt.gray()
#    ax.imshow(im)
# plt.show()
