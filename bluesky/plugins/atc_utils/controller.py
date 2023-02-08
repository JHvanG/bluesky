import os
import numpy as np
import tensorflow as tf
from tensorflow import keras
from keras import Sequential
from keras.layers import Dense, Input

from bluesky.plugins.atc_utils.state import State
from bluesky.plugins.atc_utils.replay_buffer import ReplayBuffer


class Controller(object):
    """
    This class represents the controller agent that is responsible for the centralized control.
    """
    def __init__(self):
        """
        Initialziation of the Controller Agent. This class contains all essentials to operate the DRL based plugin in
        terms of network-related processes.
        """
        # Config parameters
        self.replay_buffer = ReplayBuffer()
        self.encoding = {"HDG_L": 0, "HDG_R": 1, "DIR": 2, "LNAV": 3}
        self.num_actions = len(self.encoding)
        self.model = self._create_model()
        self.target_model = self._create_model()

    def decode_actions(self, ohe_action: list[int]) -> (bool, str, str):
        """
        This function decodes the output of the Deep-Q Network, which is a one-hot encoding of the actions of both
        aircraft in the conflict:
        [ x x x x | x x x x ]

        :param ohe_action: one-hot encoded network output
        :return: success parameter and two actions associated with the network output
        """

        if len(ohe_action) != self.num_actions * 2:
            return False, None, None

        ohe_action1 = ohe_action[:int(self.num_actions)]
        ohe_action2 = ohe_action[int(self.num_actions):int(self.num_actions*2)]

        if ohe_action1.count(1) != 1 or ohe_action2.count(1) != 1:
            return False, None, None

        action1 = list(self.encoding.keys())[list(self.encoding.values()).index(ohe_action1.index(1))]
        action2 = list(self.encoding.keys())[list(self.encoding.values()).index(ohe_action2.index(1))]

        return True, action1, action2

    def encode_actions(self, act1: str, act2: str) -> list[int]:
        """
        This function takes two string type actions and encodes them to match the model output.

        :param act1: action of the first aircraft in the conflict
        :param act2: action of the second aircraft in the conflict
        :return: binarized encoding of the actions
        """
        idx1 = self.encoding[act1]
        idx2 = self.encoding[act2]
        act1_enc = [0] * self.num_actions
        act2_enc = [0] * self.num_actions

        act1_enc[idx1] = 1
        act2_enc[idx2] = 1

        return act1_enc + act2_enc

    def convert_to_binary(self, model_output: list[float]) -> list[int]:
        """
        This function converts the model probabilistic model output to binary labels.

        :param model_output: original model output
        :return: binary list with a one at two indices indicating what action ought to be taken by the aircraft
        """
        print(model_output)
        first = model_output[:len(self.encoding)]
        second = model_output[len(self.encoding):len(self.encoding) * 2]
        print(first, second)

        max_first = max(first)
        max_second = max(second)
        first_max_encountered = False
        second_max_encountered = False

        for i in range(len(first)):
            if not first_max_encountered and first[i] == max_first:
                first[i] = 1
                first_max_encountered = True
            else:
                first[i] = 0

            if not second_max_encountered and second[i] == max_second:
                second[i] = 1
                second_max_encountered = True
            else:
                second[i] = 0

        binary = first + second
        return binary

    def store_experiences(self, state: State, act1: str, act2: str, reward: int, next_state: State):
        """
        This function saves the experience from the current action and its result.

        :param state: state from which the action was taken
        :param act1: action taken by first aircraft in the conflict
        :param act2: action taken by the second aircraft in the conflict
        :param reward: reward from the taken action
        :param next_state: state reached from the taken action
        """
        action = self.encode_actions(act1, act2)
        self.replay_buffer.store_experience(state, action, reward, next_state)
        pass

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
        state = np.asarray(state.get_state_as_list())
        input_state = tf.convert_to_tensor(state[None, :])
        print(input_state)
        action_q = self.model(input_state)
        model_output = action_q.numpy().tolist()[0]
        action = self.convert_to_binary(model_output)
        print(action)
        success, act1, act2 = self.decode_actions(action)

        if not success:
            raise Exception("Model failed to produce legitimate output")

        return act1, act2

    def save_weights(self):
        """
        This function simply saves the current model to an h5 file.
        """

        workdir = os.getcwd()
        path = os.path.join(workdir, "results/model_weights/")

        if not os.path.exists(path):
            os.makedirs(path)

        self.model.save_weights(path + "training_weights.h5")
        return

    def load_weights(self):
        """
        This function loads the model weights from a file. If the file is not present, it will initialize the model
        randomly.
        """
        workdir = os.getcwd()
        self.model.load_weights(workdir, "results/model_weights/training_weights.h5")

    def _create_model(self) -> keras.Model:
        """
        This function will build the model from scratch.

        Note: this is just a placeholder presented in a tutorial.
        :return: The complete model
        """

        q_net = Sequential()
        q_net.add(Dense(64, input_dim=12, activation='relu', kernel_initializer='he_uniform'))
        q_net.add(Dense(32, activation='relu', kernel_initializer='he_uniform'))
        q_net.add(Dense(8, activation='sigmoid', kernel_initializer='he_uniform'))
        q_net.compile(loss="binary_crossentropy", optimizer=tf.optimizers.Adam(learning_rate=0.001))    # loss='mse')
        print(q_net.summary())
        return q_net

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

            # if not done_batch[i]:
            # TODO: alter this to fit needs
            target_q_val += 0.95 * max_next_q[i]

            target_q[i][action_batch[i]] = target_q_val

        training_history = self.model.fit(x=state_batch, y=target_q, verbose=0)
        loss = training_history.history['loss']
        return loss


if __name__ == "__main__":
    controller = Controller()
    test_list = [0, 0, 0, 1, 0, 0, 1, 0]
    status, act1, act2 = controller.decode_actions(test_list)

    if not status:
        print("failure!")
    else:
        print(act1, act2)