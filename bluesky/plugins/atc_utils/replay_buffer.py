import random
import numpy as np
from collections import deque
from bluesky.plugins.atc_utils.main_utils.state import State
from bluesky.plugins.atc_utils.settings import BATCH_SIZE, BUFFER_SIZE


class ReplayBuffer(object):
    """
    This class represents the buffer used for experience replay.
    """
    def __init__(self):
        self.experience_buffer = deque(maxlen=BUFFER_SIZE)

    def store_experience(self, state: State, action: int, reward: int, next_state: State, done: bool):
        """
        Function for storing the experiences.

        :param state: state to be stored
        :param action: action that was performed
        :param reward: reward obtained from performing the action
        :param next_state: next state that was reached from the performed action
        :param done: indicates whether the state is the last state in the sequence of a conflict
        """

        self.experience_buffer.append((state.get_state_as_list(), action, reward, next_state.get_state_as_list(), done))

        return

    def sample_batch(self) -> tuple[np.array, np.array, np.array, np.array, np.array]:
        """
        Randomly samples a batch of experiences for training.

        :return: a list of experiences (state, action, reward, next state)
        """
        batch_size = min(BATCH_SIZE, len(self.experience_buffer))
        sampled_experience_batch = random.sample(self.experience_buffer, batch_size)

        state_batch = []
        action_batch = []
        reward_batch = []
        next_state_batch = []
        done_batch = []

        for experience in sampled_experience_batch:
            state_batch.append(experience[0])
            action_batch.append(experience[1])
            reward_batch.append(experience[2])
            next_state_batch.append(experience[3])
            done_batch.append(experience[4])

        return np.array(state_batch), np.array(action_batch), np.array(reward_batch), np.array(next_state_batch), np.array(done_batch)
