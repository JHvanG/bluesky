import random
import numpy as np
from collections import deque


class ReplayBuffer(object):
    """
    This class represents the buffer used for experience replay.
    """
    def __init__(self):
        self.experience_buffer = deque(maxlen=1000000)

    def store_experience(self, state, action, reward, next_state):
        """
        Function for storing the experiences.

        :param state: state to be stored
        :param action: action that was performed
        :param reward: reward obtained from performing the action
        :param next_state: next state that was reached from the performed action
        """

        self.experience_buffer.append((state, action, reward, next_state))

        return

    def sample_batch(self):
        """
        Samples a batch of experiences for training.

        :return: a list of experiences (state, action, reward, next state)
        """
        batch_size = min(128, len(self.experience_buffer))
        sampled_experience_batch = random.sample(self.experience_buffer, batch_size)

        state_batch = []
        action_batch = []
        reward_batch = []
        next_state_batch = []

        for experience in sampled_experience_batch:
            state_batch.append(experience[0])
            action_batch.append(experience[1])
            reward_batch.append(experience[2])
            next_state_batch.append(experience[3])

        return np.array(state_batch), np.array(action_batch), np.array(reward_batch), np.array(next_state_batch)
