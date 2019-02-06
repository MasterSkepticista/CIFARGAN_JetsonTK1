import tensorflow as tf
from keras.datasets import cifar10, mnist
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm       #Progressbar

print("Tensorflow version:",tf.__version__)

#Import datasets
(train_X, train_y), (test_X, test_y) = cifar10.load_data()
train_X = np.concatenate((train_X, test_X), axis = 0)/255

#plot some samples

fig, axes = plt.subplots(figsize=(15, 4), nrows=1, ncols=6, sharey=True, sharex=False)
#Deep Convolutional GAN class
for i in range(6):
    axes[i].xaxis.set_visible(False)
    axes[i].yaxis.set_visible(False)
    im = axes[i].imshow(train_X[i])

    class GAN:
        #Constructor to init
        def __init__(self, train_X, poolnumbers = 100):
            self.training_set = train_X     #Note, we don't need labels. Just Real or Fake
            self.poolnumbers = poolnumbers  #How many random numbers to pick
            self.samples = []
            self.losses = []
            self.weights = []

        #Generator DeConv network [CONSTRUCTOR]
        def __generator(self, input_layer, kernel_size = 5, reuse = False,
                        lrelu_slope = 0.2, kernel_initializer = tf.contrib.layers.xavier_initializer(),
                        training = True):
            w_init = kernel_initializer

            with tf.variable_scope('generator', reuse = reuse):
                input_dense = tf.layers.dense(inputs = input_layer, units = 2 * 2 * 256)
                input_volume = tf.reshape(input_dense, shape = (-1, 2, 2, 256))
                h1 = tf.layers.batch_normalization(inputs = input_volume, training = training)
                h1 = tf.maximum(h1 * lrelu_slope, h1)

                h2 = tf.layers.conv2d_transpose(filters = 128, strides = 2, kernel_size = kernel_size,
                                                padding = 'same', inputs = h1, activation = None,
                                                kernel_initializer = w_init)
                h2 = tf.layers.batch_normalization(inputs = h2, training = training)
                h2 = tf.maximum(h2 * lrelu_slope, h2)

                h3 = tf.layers.conv2d_transpose(filters = 64, strides = 2, kernel_size = kernel_size,
                                                padding = 'same', inputs = h2, activation = None,
                                                kernel_initializer = w_init)
                h3 = tf.layers.batch_normalization(inputs = h3, training = training)
                h3 = tf.maximum(h3 * lrelu_slope, h3)

                h4 = tf.layers.conv2d_transpose(filters = 32, strides = 2, kernel_size = kernel_size,
                                                padding = 'same', inputs = h3, activation = None,
                                                kernel_initializer = w_init)
                h4 = tf.layers.batch_normalization(inputs = h4, training = training)
                h4 = tf.maximum(lrelu_slope * h4, h4)

                logits = tf.layers.conv2d_transpose(filters = 3, strides = 2, kernel_size = kernel_size,
                                                padding = 'same', inputs = h4, activation = None,
                                                kernel_initializer = w_init)
                out = tf.tanh(x = logits)
                return out

        #Discriminator Conv network [CONSTRUCTOR]
        def __discriminator(self, input_layer, reuse = False, lrelu_slope = 0.2,
                            kernel_initializer = tf.contrib.layers.xavier_initializer(),
                            kernel_size = 5):
            w_init = kernel_initializer

            with tf.variable_scope('discriminator', reuse = reuse):
                h1 = tf.layers.conv2d(inputs = input_layer, filters = 32, strides = 2, kernel_size = kernel_size,
                                    padding = 'same', kernel_initializer = w_init)
                h1 = tf.maximum(h1, h1 * lrelu_slope)

                h2 = tf.layers.conv2d(inputs = h1, filters = 64, strides = 2, kernel_size = kernel_size,
                                    padding = 'same', kernel_initializer = w_init)
                h2 = tf.maximum(h2, h2 * lrelu_slope)

                h3 = tf.layers.conv2d(inputs = h2, filters = 128, strides = 2, kernel_size = kernel_size,
                                    padding = 'same', kernel_initializer = w_init)
                h3 = tf.maximum(h3, h3 * lrelu_slope)

                h4 = tf.layers.conv2d(inputs = h3, filters = 256, strides = 2, kernel_size = kernel_size,
                                    padding = 'same', kernel_initializer = w_init)
                h4 = tf.maximum(h4, h4 * lrelu_slope)

                flatten = tf.reshape(tensor = h4, shape = (-1, 2*2*256))
                logits = tf.layers.dense(inputs = flatten, units = 1, activation = None, kernel_initializer = w_init)
                out = tf.sigmoid(x = logits)
                return out, logits

        def __inputs(self):

            gen_input = tf.placeholder(shape = (None, self.poolnumbers), dtype = tf.float32)
            real_input = tf.placeholder(shape = (None, 32, 32, 3), dtype = tf.float32)
            return gen_input, real_input

        def __setup_losses_and_optimizers(self, lr = 0.0005, beta1 = 0.5, beta2 = 0.999):
            tf.reset_default_graph()

            gen_input, real_input = self.__inputs()
            gen_images = self.__generator(input_layer = gen_input, kernel_size = 5, reuse = False,
                                        lrelu_slope = 0.2, kernel_initializer = tf.contrib.layers.xavier_initializer(),
                                        training = True)
            disc_output_real_image, disc_logits_real_image = self.__discriminator(input_layer = real_input,
                                                                                reuse = False, lrelu_slope = 0.2,
                                                                                kernel_initializer = tf.contrib.layers.xavier_initializer(),
                                                                                kernel_size = 5)

            disc_output_gen_image, disc_logits_gen_image = self.__discriminator(input_layer = gen_images,
                                                                                reuse = True, lrelu_slope = 0.2,
                                                                                kernel_initializer = tf.contrib.layers.xavier_initializer(),
                                                                                kernel_size = 5)
            #Losses

            gen_loss = tf.reduce_mean(tf.losses.sigmoid_cross_entropy(logits = disc_logits_gen_image,
                                    multi_class_labels = tf.ones_like(disc_logits_gen_image)))

            disc_loss_real_images = tf.reduce_mean(tf.losses.sigmoid_cross_entropy(logits = disc_logits_real_image,
                                    multi_class_labels = tf.ones_like(disc_logits_real_image)))
            disc_loss_gen_images = tf.reduce_mean(tf.losses.sigmoid_cross_entropy(logits = disc_logits_gen_image,
                                    multi_class_labels = tf.zeros_like(disc_logits_gen_image)))
            disc_loss = disc_loss_gen_images + disc_loss_real_images

            #try glancing again
            generator_variables = [var for var in tf.trainable_variables() if var.name.startswith('generator')]
            discriminator_variables = [var for var in tf.trainable_variables() if var.name.startswith('discriminator')]


            with tf.control_dependencies(tf.get_collection(tf.GraphKeys.UPDATE_OPS)):
                generator_optimizer = tf.train.AdamOptimizer(learning_rate=lr, beta1=beta1, beta2=beta2).minimize(gen_loss, var_list=generator_variables)
                discriminator_optimizer = tf.train.AdamOptimizer(learning_rate=lr, beta1=beta1, beta2=beta2).minimize(disc_loss, var_list=discriminator_variables)

            return discriminator_optimizer, generator_optimizer, disc_loss, gen_loss, gen_input, real_input

        def train(self, batch_size = 128, epochs = 100):
            d_opt, g_opt, d_loss, g_loss, gen_input, real_input = self.__setup_losses_and_optimizers()

            with tf.Session() as sess:

                sess.run(tf.global_variables_initializer())

                for epoch in tqdm(range(epochs)):
                    for step, batch in enumerate(self.__next_batch(self.training_set, batch_size)):
                        noise = np.random.uniform(low = -1, high = 1, size = (batch_size, self.poolnumbers))

                        _ = sess.run(g_opt, feed_dict = {gen_input: noise, real_input: batch})
                        _ = sess.run(d_opt, feed_dict = {gen_input: noise, real_input: batch})

                        gen_loss, disc_loss = sess.run([g_loss, d_loss], feed_dict = {gen_input: noise, real_input: batch})

                        self.losses.append((gen_loss, disc_loss))

                    if epoch%1 == 0:
                        sample_noise = np.random.uniform(low = -1, high = 1, size = (72, self.poolnumbers))

                        gen_samples = sess.run(self.__generator(gen_input, reuse = True, training = False), feed_dict = {gen_input: sample_noise})

                        self.samples.append(gen_samples)
                        _ = self.view_samples(-1, self.samples, 6, 12, figsize = (8, 5))
                        plt.show()

        def __next_batch(self, data, batch_size = 128):
            number_of_partitions = data.shape[0]//batch_size
            np.random.shuffle(self.training_set)

            for batch in np.array_split(self.training_set[:number_of_partitions * batch_size], number_of_partitions):
                yield batch * 2 - 1

        def view_samples(self, epoch, samples, nrows, ncols, figsize=(5, 5)):

            # ge the figure and the axes
            fig, axes = plt.subplots(figsize=figsize, nrows=nrows, ncols=ncols, sharey=True, sharex=True)

            # draw the samples
            for ax, img in zip(axes.flatten(), samples[epoch]):
                ax.axis('off')
                img = ((img - img.min())*255 / (img.max() - img.min())).astype(np.uint8)
                ax.set_adjustable('box-forced')
                im = ax.imshow(img, aspect='equal')
            plt.subplots_adjust(wspace=0, hspace=0)
            return fig, axes



gan = GAN(train_X)
gan.train(batch_size = 64, epochs = 30)
