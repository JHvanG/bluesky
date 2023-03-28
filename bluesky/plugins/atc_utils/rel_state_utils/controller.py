import os
import random
import numpy as np
import tensorflow as tf
from tensorflow import keras
from keras import Sequential
from keras.layers import Dense, Input

from bluesky.plugins.atc_utils.rel_state_utils.state import State
from bluesky.plugins.atc_utils.replay_buffer import ReplayBuffer


class Controller(object):
    """
    This class represents the controller agent that is responsible for the centralized control.
    """
    def __init__(self):
        """
        Initialization of the Controller Agent. This class contains all essentials to operate the DRL based plugin in
        terms of network-related processes.
        """
        # Config parameters
        self.epsilon = 1.0      # exploration parameter
        self.max_epsilon = 1.0
        self.min_epsilon = 0.05
        self.epsilon_decay = 0.1
        self.epsilons = [self.epsilon]
        self.replay_buffer = ReplayBuffer()
        self.encoding = {"HDG_L": 0, "HDG_R": 1, "LNAV": 2}
        self.num_actions = len(self.encoding)
        self.model = self._create_model()
        self.target_model = self._create_model()

    def select_action(self, model_output: list[float]) -> str:
        """
        This function selects the action with the highest Q-value from the model output.

        :param model_output: model output (Q-values)
        :return: string of associated action
        """

        highest_qs = [i for i, x in enumerate(model_output) if x == max(model_output)]
        idx = random.choice(highest_qs)
        action = list(self.encoding.keys())[idx]

        return action

    def store_experiences(self, state: State, act_str: str, reward: int, next_state: State):
        """
        This function saves the experience from the current action and its result.

        :param state: state from which the action was taken
        :param act_str: action taken by the aircraft in the conflict as the string command
        :param reward: reward from the taken action
        :param next_state: state reached from the taken action
        """
        action = self.encoding[act_str]
        self.replay_buffer.store_experience(state, action, reward, next_state)
        return

    def load_experiences(self):
        """
        Function that allows the plugin to load the replay buffer.

        :return: batch of the replay buffer
        """
        return self.replay_buffer.sample_batch()

    def act(self, state: State) -> (str, str):
        """
        Returns actions for the given state.

        :param state: current state of the two aircraft in conflict.
        :return: two strings containing the actions to be taken.
        """

        # print("Predicting on: {}".format(state.get_state_as_list()))

        # exploration
        if random.random() < self.epsilon:
            # TODO: only do this when training
            action = random.choice(list(self.encoding.keys()))
            return action

        state = np.asarray(state.get_state_as_list())
        input_state = tf.convert_to_tensor(state[None, :])

        action_q = self.model(input_state)
        model_output = action_q.numpy().tolist()[0]

        action = self.select_action(model_output)

        return action

    def save_weights(self, name: str = ""):
        """
        This function simply saves the current model to an h5 file.
        """

        workdir = os.getcwd()
        path = os.path.join(workdir, "results/model_weights/")

        if not os.path.exists(path):
            os.makedirs(path)

        self.model.save_weights(path + "training_weights_com" + name + ".h5")

        return

    def load_weights(self, name: str = ""):
        """
        This function loads the model weights from a file. If the file is not present, it will initialize the model
        randomly.
        """

        workdir = os.getcwd()
        self.model.load_weights(workdir, "results/model_weights/training_weights_com" + name + ".h5")

        return

    def _create_model(self) -> keras.Model:
        """
        This function will build the model from scratch.

        Note: this is just a placeholder presented in a tutorial.
        :return: The complete model
        """

        q_net = Sequential()
        q_net.add(Dense(64, input_dim=11, activation='relu', kernel_initializer='he_uniform'))
        q_net.add(Dense(32, activation='relu', kernel_initializer='he_uniform'))
        q_net.add(Dense(3, activation='sigmoid', kernel_initializer='he_uniform'))
        q_net.compile(loss="mse", optimizer=tf.optimizers.Adam(learning_rate=0.001))
        print(q_net.summary())

        return q_net

    def update_target_model(self):
        """
        Every C steps, the target model is updated with the weights of the current model.
        """
        self.target_model.set_weights(self.model.get_weights())
        return

    def train(self, batch):
        """
        Function responsible for training the network. WORK ON THIS!!!!!!

        :param batch: a batch of experiences
        :return: loss of the network
        """
        state_batch, action_batch, reward_batch, next_state_batch = batch
        current_q = self.model(state_batch).numpy()
        target_q = np.copy(current_q)
        next_q = self.target_model(next_state_batch).numpy()
        max_next_q = np.amax(next_q, axis=1)

        for i in range(state_batch.shape[0]):
            target_q_val = reward_batch[i]

            # TODO: alter this to fit needs
            target_q_val += 0.95 * max_next_q[i]

            target_q[i][action_batch[i]] = target_q_val

        training_history = self.model.fit(x=state_batch, y=target_q, verbose=0)
        loss = training_history.history['loss']

        # apply exploration decay
        self.epsilon = max(self.min_epsilon, self.epsilon - (self.max_epsilon - self.min_epsilon) * self.epsilon_decay)
        self.epsilons.append(self.epsilon)

        return loss