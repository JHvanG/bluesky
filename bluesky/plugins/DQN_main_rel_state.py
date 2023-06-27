"""
This is the main plugin for the DQN-based controller agent, using the center-of-mass, relative state definition.
"""

import time

# Import the global bluesky objects. Uncomment the ones you need
import numpy as np

import bluesky as bs

from bluesky.tools import geo
from bluesky import stack, traf

from bluesky.plugins.atc_utils.rel_state_utils.state import State
from bluesky.plugins.atc_utils.rel_state_utils.controller import Controller
from bluesky.plugins.atc_utils import prox_util as pu
from bluesky.plugins.atc_utils import dqn_util as du
from cpa import closest_point_of_approach as cpa
from bluesky.plugins.atc_utils.settings import EVAL_COOLDOWN, EPISODE_LIMIT, TIME_LIMIT, \
                                               CONFLICT_LIMIT, TRAIN_INTERVAL, TARGET_INTERVAL, \
                                               SEP_REP_HOR, EPSILON_DECAY, MIN_EPSILON, NUM_TRANS, \
                                               BATCH_SIZE, BUFFER_SIZE, LOSS_FUNCTION, REWARD_FUNCTION, \
                                               TRAIN_LENGTH, VALIDATION_LENGTH, SEP_REWARD, LR

# EXPERIMENT_NAME = "_{}tran_{}_{}seprew_{}_{}batch_{}buffer_{}train_{}update_{}alert_{}decay_{}epsilon".format(
#     NUM_TRANS, REWARD_FUNCTION, SEP_REWARD, LOSS_FUNCTION, BATCH_SIZE, BUFFER_SIZE,
#     TRAIN_INTERVAL, TARGET_INTERVAL, SEP_REP_HOR, EPSILON_DECAY, MIN_EPSILON).replace(".", "_")

EXPERIMENT_NAME = "120_{}tran_test_{}_{}batch_{}buffer".format(NUM_TRANS, REWARD_FUNCTION, BATCH_SIZE, BUFFER_SIZE).replace(".", "_")

EPISODE_COUNTER = 0                         # counter to keep track of how many episodes have passed
VALIDATION_COUNTER = 0                      # counter to keep track of how many episodes the validation has taken
START = 0                                   # start time
TIMER = 0                                   # counter to keep track of how many update calls were made this episode

VALIDATING = False                          # boolean to indicate whether the validation phase has commenced

CONFLICTS_IN_COOLDOWN = []                  # list of aircraft that are currently in conflict with one another
PREVIOUS_ACTIONS = []                       # buffer for previous actions with the given state and the aircraft pair
KNOWN_CONFLICTS = []                        # list of conflict pairs that have been counted to the conflict total
LoS_PAIRS = []                              # list of aircraft that have currently lost separation

TOTAL_REWARD = 0                            # storage for total obtained reward this episode
N_CONFLICTS = 0                             # counter for the number of conflicts that have been encountered
N_RESOLVED = 0                              # test for counting fails and successes

VAL_AVG_EP_REWARDS = []                     # list of average rewards for validation episodes
VAL_EP_CONFLICTS = []                       # list of n conflicts per validation episode
VAL_EP_LoS = []                             # list of m losses of separation per validation episode
VAL_EP_LEFT = []                            # list of counts for left action in validation episodes
VAL_EP_RIGHT = []                           # list of counts for right action in validation episodes
VAL_EP_LNAV = []                            # list of counts for LNAV action in validation episodes

# CONTROLLER = Controller()                 # atc agent based on a DQN
CONTROLLER = Controller(EXPERIMENT_NAME)    # atc agent based on a DQN


### Initialization function of your plugin. Do not change the name of this
### function, as it is the way BlueSky recognises this file as a plugin.
def init_plugin():
    # Addtional initilisation code
    print("Writing with extension: {}".format(EXPERIMENT_NAME))
    print(f"{NUM_TRANS} approaches\n{REWARD_FUNCTION} reward\n{BATCH_SIZE} batch\n{BUFFER_SIZE} buffer\n{LR} learning rate\n")

    # Configuration parameters
    config = {
        # The name of your plugin
        'plugin_name': 'DQNRELATIVE',

        # The type of this plugin. For now, only simulation plugins are possible.
        'plugin_type': 'sim',

        # Update interval in seconds. By default, your plugin's update function(s)
        # are called every timestep of the simulation. If your plugin needs less
        # frequent updates provide an update interval.
        # Delta T = 0.05s in the simulation
        # NOTE: CHANGED THIS FROM 0.0
        'update_interval': 5.0,

        # The update function is called after traffic is updated. Use this if you
        # want to do things as a result of what happens in traffic. If you need to
        # something before traffic is updated please use preupdate.
        'update': update,

        # If your plugin has a state, you will probably need a reset function to
        # clear the state in between simulations.
        'reset': reset
    }

    stackfunctions = {
        # The command name for your function
        'DQNRELATIVE': [
            # A short usage string. This will be printed if you type HELP <name> in the BlueSky console
            'DQNRELATIVE argument',

            # A list of the argument types your function accepts. For a description of this, see ...
            'txt',

            # The name of your function in this plugin
            dqn_main_relative,

            # a longer help text of your function.
            'First test plugin to help with plugin development.']
    }

    # init_plugin() should always return these two dicts.
    return config, stackfunctions


def get_current_state(ac1: str, ac2: str) -> State:
    """
    This function returns all information required to build a state.

    :param ac1: string of aircraft 1's ID
    :param ac2: string of aircraft 2's ID
    :return: current state given the two aircraft
    """

    lat1, lon1, alt1, hdg1, rte1 = du.load_state_data(ac1)
    lat2, lon2, alt2, hdg2, rte2 = du.load_state_data(ac2)
    com_bearing, com_dist, com_hdg = pu.get_centre_of_mass(ac1)

    bearing, dist = geo.qdrdist(lat1, lon1, lat2, lon2)  # bearing, distance (nm)

    return State(bearing, dist, alt1, hdg1, rte1, alt2, hdg2, rte2,
                 com_bearing, com_dist, com_hdg)


def update_stored_conflicts():
    """
    This function removes any conflicts that have been counted and are no longer occurring, as well as removing any
    conflict that resulted in a loss of separation where the planes have now separated beyond alerting distance.
    """

    for (ac1, ac2) in KNOWN_CONFLICTS:
        if not pu.is_within_alert_distance(ac1, ac2):
            KNOWN_CONFLICTS.remove((ac1, ac2))

    for (ac1, ac2) in CONFLICTS_IN_COOLDOWN:
        if not pu.is_within_alert_distance(ac1, ac2):
            CONFLICTS_IN_COOLDOWN.remove((ac1, ac2))

    return


def waiting_for_reward(ac1: str, ac2: str) -> bool:
    """
    This function checks whether the provided aircraft have received an instruction and have not gotten a reward.

    :param ac1: string of aircraft id of first aircraft
    :param ac2: string of aircraft id of second aircraft
    :return: True if still in previous actions, else False
    """

    for _, _, stored_ac1, stored_ac2, _, _ in PREVIOUS_ACTIONS:
        if ac1 == stored_ac1 and ac2 == stored_ac2:
            return True
    return False


def get_pairs_waiting_for_reward():
    """
    This function returns a list of aircraft pairs that currently await feedback on their previously received instruction.

    :return: list of aircraft pairs
    """

    pairs_waiting_for_reward = []
    for _, _, ac1, ac2, _, _ in PREVIOUS_ACTIONS:
        pairs_waiting_for_reward.append((ac1, ac2))

    return pairs_waiting_for_reward


def update():
    """
    This is the main function of the plugin, which is called each update.
    """

    global TIMER
    global START
    global TOTAL_REWARD
    global N_CONFLICTS
    global PREVIOUS_ACTIONS

    global N_RESOLVED

    # TODO: check for training or testing episode
    #       For training we do what we do now
    #       For testing, we remove the randomness from action selection, keep most of the logic but do not train
    #       we can remove the experience buffer for testing as well

    if TIMER == 0:
        print("Plugin reset finished at: {}".format(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))))
        START = time.time()

    TIMER = TIMER + 1

    # if TIMER == TIME_LIMIT or N_CONFLICTS >= CONFLICT_LIMIT:
    if TIMER == TIME_LIMIT or N_RESOLVED >= CONFLICT_LIMIT:
        stack.stack("RESET")
        return

    update_stored_conflicts()

    # first check if an instruction was given at t - 1, then the experience buffer needs to be updated
    if PREVIOUS_ACTIONS:
        actions_in_cooldown = []

        while PREVIOUS_ACTIONS:
            prev_state, action, ac1, ac2, cooldown, cpa_dist = PREVIOUS_ACTIONS.pop()

            # check if action has had chance to have effect
            if cooldown < EVAL_COOLDOWN and not pu.is_loss_of_separation(ac1, ac2):
                actions_in_cooldown.append((prev_state, action, ac1, ac2, cooldown + 1, cpa_dist))
            elif ac1 in traf.id and ac2 in traf.id:
                current_state = get_current_state(ac1, ac2)

                # the reward is based on the current state, so can be taken directly from info of the simulator
                if REWARD_FUNCTION == "LNAV":
                    LoS, reward = du.get_reward_lnav_incentive(ac1, ac2, action)
                elif REWARD_FUNCTION == "SPARSE":
                    LoS, reward = du.get_sparse_reward(ac1, ac2)
                else:
                    LoS, reward = du.get_reward(ac1, ac2, cpa_dist)
                TOTAL_REWARD += reward

                if LoS:
                    CONFLICTS_IN_COOLDOWN.append((ac1, ac2))

                # if a conflict has been resolved or resulted in a loss of separation, the done parameter is set to True
                if not pu.is_within_alert_distance(ac1, ac2) or pu.is_loss_of_separation(ac1, ac2):
                    done = True
                else:
                    done = False

                if done:
                    N_RESOLVED += 1

                if not VALIDATING:
                    CONTROLLER.store_experiences(prev_state, action, reward, current_state, done)

        # keep actions that were still in cooldown
        if actions_in_cooldown:
            PREVIOUS_ACTIONS = actions_in_cooldown

    # this variable contains all the closest conflict pairs
    current_conflict_pairs = pu.get_conflict_pairs(CONFLICTS_IN_COOLDOWN)  # list of tuples

    pairs_waiting_for_reward = get_pairs_waiting_for_reward()

    # aircraft not in current conflicts that received instructions and a reward can return to their flightplans
    du.allow_resume_navigation(current_conflict_pairs, pairs_waiting_for_reward)

    for (ac1, ac2) in current_conflict_pairs:

        # update conflict counter
        if not (ac1, ac2) in KNOWN_CONFLICTS:
            KNOWN_CONFLICTS.append((ac1, ac2))
            N_CONFLICTS += 1

        # update known conflicts to include the current conflict
        if not waiting_for_reward(ac1, ac2):
            # instruct aircraft
            state = get_current_state(ac1, ac2)
            action = CONTROLLER.act(state, VALIDATING)
            du.handle_instruction(ac1, action)

            # previous actions are maintained to apply rewards in the next state
            cpa_dist = cpa.closest_point_of_approach(du.get_cpa_data(ac1), du.get_cpa_data(ac2))
            PREVIOUS_ACTIONS.append((state, action, ac1, ac2, 0, cpa_dist))

    return


def reset():
    """
    Reset after episode has finished.
    """

    print("Plugin reset at: {}".format(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))))
    print("resetting main plugin")

    global CONFLICTS_IN_COOLDOWN
    global PREVIOUS_ACTIONS
    global LoS_PAIRS

    global EPISODE_COUNTER
    global TOTAL_REWARD
    global N_CONFLICTS
    global TIMER
    global START

    global VALIDATION_COUNTER
    global VAL_AVG_EP_REWARDS
    global VAL_EP_CONFLICTS
    global VAL_EP_RIGHT
    global VAL_EP_LEFT
    global VAL_EP_LNAV
    global VAL_EP_LoS
    global VALIDATING

    global N_RESOLVED

    print(f"{N_RESOLVED} conflicts completed (fail/success)")

    if not VALIDATING:
        EPISODE_COUNTER += 1

        print("Episode {} finished".format(EPISODE_COUNTER))
        print("{} conflicts and {} losses of separation".format(N_CONFLICTS, du.N_LoS))

        if EPISODE_COUNTER % TRAIN_INTERVAL == 0:
            loss = CONTROLLER.train(CONTROLLER.load_experiences())

            if EPISODE_COUNTER % TARGET_INTERVAL == 0:
                CONTROLLER.update_target_model()

            data = {
                "episode": EPISODE_COUNTER,
                "loss": loss,
                "average reward": TOTAL_REWARD / du.N_INSTRUCTIONS,
                # "conflicts": N_CONFLICTS,
                "conflicts": N_RESOLVED,
                "duration": round(time.time() - START, 2),
                "epsilon": CONTROLLER.epsilon
            }

            du.write_episode_info(data, EXPERIMENT_NAME)

        else:
            data = {
                "episode": EPISODE_COUNTER,
                "loss": None,
                "average reward": TOTAL_REWARD / du.N_INSTRUCTIONS,
                # "conflicts": N_CONFLICTS,
                "conflicts": N_RESOLVED,
                "duration": round(time.time() - START, 2),
                "epsilon": CONTROLLER.epsilon
            }

            du.write_episode_info(data, EXPERIMENT_NAME)
    else:
        VALIDATION_COUNTER += 1
        VAL_AVG_EP_REWARDS.append(TOTAL_REWARD / du.N_INSTRUCTIONS)
        # VAL_EP_CONFLICTS.append(N_CONFLICTS)
        VAL_EP_CONFLICTS.append(N_RESOLVED)
        VAL_EP_LoS.append(du.N_LoS)
        VAL_EP_LEFT.append(du.N_LEFT)
        VAL_EP_RIGHT.append(du.N_RIGHT)
        VAL_EP_LNAV.append(du.N_LNAV)

    # check if we reached a validation point, or, when already validating, if we can stop and save the results
    if not VALIDATING and EPISODE_COUNTER % TRAIN_LENGTH == 0:
        print(f"episode: {EPISODE_COUNTER}, going over to validation")
        VALIDATING = True

    elif VALIDATING and VALIDATION_COUNTER % VALIDATION_LENGTH == 0:
        VALIDATING = False

        data = {
            "rewards": np.mean(VAL_AVG_EP_REWARDS),
            "rewardsstd": np.std(VAL_AVG_EP_REWARDS),
            "conflicts": np.mean(VAL_EP_CONFLICTS),
            "LoS": np.mean(VAL_EP_LoS),
            "LoSstd": np.std(VAL_EP_LoS),
            "Left": np.mean(VAL_EP_LEFT),
            "Leftstd": np.std(VAL_EP_LEFT),
            "Right": np.mean(VAL_EP_RIGHT),
            "Rightstd": np.std(VAL_EP_RIGHT),
            "LNAV": np.mean(VAL_EP_LNAV),
            "LNAVstd": np.std(VAL_EP_LNAV)
        }

        du.write_validation_info(data, EXPERIMENT_NAME)
        CONTROLLER.update_best_weights(np.mean(VAL_EP_LoS), EXPERIMENT_NAME)

        print(f"episode: {EPISODE_COUNTER}, going over to training")

        VALIDATION_COUNTER = 0
        VAL_AVG_EP_REWARDS = []
        VAL_EP_CONFLICTS = []
        VAL_EP_LoS = []
        VAL_EP_LEFT = []
        VAL_EP_LNAV = []
        VAL_EP_RIGHT = []

    # reset all global variables
    CONFLICTS_IN_COOLDOWN = []
    PREVIOUS_ACTIONS = []
    LoS_PAIRS = []

    TOTAL_REWARD = 0
    N_CONFLICTS = 0
    TIMER = 0
    START = 0

    N_RESOLVED = 0

    du.reset_variables()

    if EPISODE_COUNTER >= EPISODE_LIMIT:
        print("Reached stopping condition")
        print("Epsilons: {}".format(CONTROLLER.epsilons))
        stack.stack("STOP")

    stack.stack("TAXI OFF")
    stack.stack("FF")

    return


### Other functions of your plugin
def dqn_main_relative(argument):
    """
    I doubt we need this function. This is purely for initialization

    :param argument:
    """
    pass