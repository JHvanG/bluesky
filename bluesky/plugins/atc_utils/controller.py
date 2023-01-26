import numpy as np
import tensorflow as tf
from bluesky.plugins.atc_utils.replay_buffer import ReplayBuffer
from bluesky.plugins.atc_utils.state import State
from tensorflow import keras
from keras import layers


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
        self.model = self._create_model()
        self.encoding = {"HDG_L": 0, "HDG_R": 1, "DIR": 2, "LNAV": 3}
        self.num_actions = len(self.encoding)

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

    def store(self, state: State, act1: str, act2: str, reward: int, next_state: State):
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

    def act(self, state) -> (str, str):
        """
        Returns actions for the given state.

        :param state: current state of the two aircraft in conflict.
        :return: two strings containing the actions to be taken.
        """

        model_output = self.model.predict(state)
        success, act1, act2 = self.decode_actions(model_output)

        if not success:
            raise Exception("Model failed to produce legitimate output")

        return act1, act2

    def _create_model(self) -> keras.Model:
        """
        This function will build the model from scratch.

        Note: this is just a placeholder presented in a tutorial.
        :return: The complete model
        """

        return

    def train(self, batch):
        """
        Function responsible for training the network.

        :param batch: a batch of experiences
        :return: loss of the network
        """
        loss = 0  # We put a 0 loss as placeholder
        return loss


if __name__ == "__main__":
    controller = Controller()
    test_list = [0, 0, 0, 1, 0, 0, 1, 0]
    status, act1, act2 = controller.decode_actions(test_list)

    if not status:
        print("failure!")
    else:
        print(act1, act2)