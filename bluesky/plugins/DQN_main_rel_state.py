"""
This is the main plugin for the DQN-based controller agent, using the center-of-mass, relative state definition.
"""

import os
import csv
import time

# Import the global bluesky objects. Uncomment the ones you need
from bluesky.tools import geo
from bluesky import stack, traf

from bluesky.plugins.atc_utils.rel_state_utils.state import State
from bluesky.plugins.atc_utils.rel_state_utils.controller import Controller
from bluesky.plugins.atc_utils import prox_util as pu
from bluesky.plugins.atc_utils import dqn_util as du
from bluesky.plugins.atc_utils.settings import SAVE_RESULTS, EVAL_COOLDOWN, EPISODE_LIMIT, TIME_LIMIT, \
                                                CONFLICT_LIMIT, TRAIN_INTERVAL, TARGET_INTERVAL, \
                                                HDG_CHANGE, SEP_REP_HOR, EPSILON_DECAY

# LET OP: DE RIVER1D TRANSITION IS NU VERKORT MET EEN WAYPOINT!!!!!!!

EXPERIMENT_NAME = "_two_transitions_spaced_{}deg_{}nm_{}decay".format(HDG_CHANGE, SEP_REP_HOR, EPSILON_DECAY).replace(".", "_")

EPISODE_COUNTER = 0                     # counter to keep track of how many episodes have passed
START = 0                               # start time
TIMER = 0                               # counter to keep track of how many update calls were made this episode

CONFLICTS_IN_COOLDOWN = []              # list of aircraft that are currently in conflict with one another
PREVIOUS_ACTIONS = []                   # buffer for previous actions with the given state and the aircraft pair
KNOWN_CONFLICTS = []                    # list of conflict pairs that have been counted to the conflict total
LoS_PAIRS = []                          # list of aircraft that have currently lost separation

TOTAL_REWARD = 0                        # storage for total obtained reward this episode
N_CONFLICTS = 0                         # counter for the number of conflicts that have been encountered

CONTROLLER = Controller()               # atc agent based on a DQN


### Initialization function of your plugin. Do not change the name of this
### function, as it is the way BlueSky recognises this file as a plugin.
def init_plugin():
    # Addtional initilisation code
    print("Writing with extension: {}".format(EXPERIMENT_NAME))

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

    # TODO: remove training results (or rename to other name or sth)
    # TODO: allow for running by loading best weights

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

    # TODO: verify that this is correct for the bearing
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
    for _, _, stored_ac1, stored_ac2, _ in PREVIOUS_ACTIONS:
        if ac1 == stored_ac1 and ac2 == stored_ac2:
            return True
    return False


def update():
    """
    This is the main function of the plugin, which is called each update.
    """

    # ------------------------------------------------------------------------------------------------------------------
    # DONE: compute centre of mass and average heading
    # DONE: redefine state space
    # DONE: give action for single plane for only closest conflict
    # TODO: increase action space to also do nothing or do more drastic turns?
    # DONE: give reward based on distance to conflict --> the further the better
    # DONE: start with just two transitions
    # DONE: register route number
    # DONE: get_current_state
    # DONE: handle_instructions
    # ------------------------------------------------------------------------------------------------------------------

    global TIMER
    global START
    global TOTAL_REWARD
    global N_CONFLICTS
    global PREVIOUS_ACTIONS

    if TIMER == 0:
        print("Plugin reset finished at: {}".format(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))))
        START = time.time()

    TIMER = TIMER + 1

    if TIMER == TIME_LIMIT or N_CONFLICTS >= CONFLICT_LIMIT:
        stack.stack("RESET")
        return

    update_stored_conflicts()

    # first check if an instruction was given at t - 1, then the experience buffer needs to be updated
    if PREVIOUS_ACTIONS:
        actions_in_cooldown = []

        while PREVIOUS_ACTIONS:
            prev_state, action, ac1, ac2, cooldown = PREVIOUS_ACTIONS.pop()

            # check if action has had chance to have effect
            if cooldown < EVAL_COOLDOWN and not pu.is_loss_of_separation(ac1, ac2):
                actions_in_cooldown.append((prev_state, action, ac1, ac2, cooldown + 1))
            elif ac1 in traf.id and ac2 in traf.id:
                current_state = get_current_state(ac1, ac2)

                # the reward is based on the current state, so can be taken directly from info of the simulator
                LoS, reward = du.get_reward(ac1, ac2)
                TOTAL_REWARD += reward

                if LoS:
                    CONFLICTS_IN_COOLDOWN.append((ac1, ac2))

                CONTROLLER.store_experiences(prev_state, action, reward, current_state)

        # keep actions that were still in cooldown
        if actions_in_cooldown:
            PREVIOUS_ACTIONS = actions_in_cooldown

    # this variable contains all the closest conflict pairs
    current_conflict_pairs = pu.get_conflict_pairs(CONFLICTS_IN_COOLDOWN)  # list of tuples

    # aircraft not in current conflicts that received instructions can return to their flightplans
    du.allow_resume_navigation(current_conflict_pairs)

    for (ac1, ac2) in current_conflict_pairs:

        # update conflict counter
        if not (ac1, ac2) in KNOWN_CONFLICTS:
            KNOWN_CONFLICTS.append((ac1, ac2))
            N_CONFLICTS += 1

        # update known conflicts to include the current conflict
        if not waiting_for_reward(ac1, ac2):
            # instruct aircraft
            state = get_current_state(ac1, ac2)
            action = CONTROLLER.act(state)
            du.handle_instruction(ac1, action)

            # previous actions are maintained to apply rewards in the next state
            PREVIOUS_ACTIONS.append((state, action, ac1, ac2, 0))

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

    EPISODE_COUNTER += 1

    print("Episode {} finished".format(EPISODE_COUNTER))
    print("{} conflicts and {} losses of separation".format(N_CONFLICTS, du.N_LoS))

    if EPISODE_COUNTER % TRAIN_INTERVAL == 0:
        loss = CONTROLLER.train(CONTROLLER.load_experiences())
        CONTROLLER.save_weights(name=EXPERIMENT_NAME)

        if EPISODE_COUNTER % TARGET_INTERVAL == 0:
            CONTROLLER.update_target_model()

        data = {
            "episode": EPISODE_COUNTER,
            "loss": loss[0],
            "average reward": TOTAL_REWARD / du.N_INSTRUCTIONS,
            "conflicts": N_CONFLICTS,
            "duration": round(time.time() - START, 2),
            "epsilon": CONTROLLER.epsilon
        }

        du.write_episode_info(data, EXPERIMENT_NAME)
    else:
        data = {
            "episode": EPISODE_COUNTER,
            "loss": None,
            "average reward": TOTAL_REWARD / du.N_INSTRUCTIONS,
            "conflicts": N_CONFLICTS,
            "duration": round(time.time() - START, 2),
            "epsilon": CONTROLLER.epsilon
        }

        du.write_episode_info(data, EXPERIMENT_NAME)

    # reset all global variables
    CONFLICTS_IN_COOLDOWN = []
    PREVIOUS_ACTIONS = []
    LoS_PAIRS = []

    TOTAL_REWARD = 0
    N_CONFLICTS = 0
    TIMER = 0
    START = 0

    du.reset_variables()

    if EPISODE_COUNTER == EPISODE_LIMIT:
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