import random
import numpy as np
from collections import deque


class ReplayBuffer:
    """
    This class represents the buffer used for experience replay.
    """
    def __init__(self):
        self.experience_buffer = deque(maxlen=1000000)

    def store_experience(self, state, next_state, reward, action):
        """
        Function for storing the experiences.

        :param state: state to be stored
        :param next_state: next state that was reached from the performed action
        :param reward: reward obtained from performing the action
        :param action: action that was performed
        :return: ...
        """

        return

    def sample_batch(self):
        """
        Samples a batch of experiences for training purposes.

        :return: a batch of experiences
        """
        batch = []  # Put an empty list as placeholder
        return batch