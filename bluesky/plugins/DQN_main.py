"""
This is the main plugin for the DQN-based controller agent, using the center-of-mass, absolute state definition.
"""

import os
import csv
import time

# Import the global bluesky objects. Uncomment the ones you need
from bluesky import stack, traf

from bluesky.plugins.atc_utils.main_utils.state import State
from bluesky.plugins.atc_utils.main_utils.controller import Controller
from bluesky.plugins.atc_utils import prox_util as pu
from bluesky.plugins.atc_utils import dqn_util as du

# LET OP: DE RIVER1D TRANSITION IS NU VERKORT MET EEN WAYPOINT!!!!!!!

EXPERIMENT_NAME = "_two_transitions_cooldown_early_LoS_slow_decay_more_spacing_45_5nm_5forSep"
SAVE_RESULTS = True

EVAL_COOLDOWN = 4  # cooldown to let action take effect before applying reward

EPISODE_COUNTER = 0  # counter to keep track of how many episodes have passed
EPISODE_LIMIT = 4000  # limits the amount of episodes
START = 0  # start time
TIMER = 0  # counter to keep track of how many update calls were made this episode
TIME_LIMIT = 720  # 1440 updates equates to approximately 2 hours of simulation time
CONFLICT_LIMIT = 50  # NOTE: rather randomly selected

CONFLICTS_IN_COOLDOWN = []  # list of aircraft that are currently in conflict with one another
PREVIOUS_ACTIONS = []  # buffer for previous actions with the given state and the aircraft pair
KNOWN_CONFLICTS = []  # list of conflict pairs that have been counted to the conflict total
LoS_PAIRS = []  # list of aircraft that have currently lost separation

TOTAL_REWARD = 0  # storage for total obtained reward this episode
N_INSTRUCTIONS = 0  # counter for the number of instructions given
N_CONFLICTS = 0  # counter for the number of conflicts that have been encountered

TRAIN_INTERVAL = 2  # the number of episodes before retraining the network
TARGET_INTERVAL = 100  # the number of episodes before updating the target network

CONTROLLER = Controller()  # atc agent based on a DQN


### Initialization function of your plugin. Do not change the name of this
### function, as it is the way BlueSky recognises this file as a plugin.
def init_plugin():
    # Addtional initilisation code
    print("Writing with extension: {}".format(EXPERIMENT_NAME))

    # Configuration parameters
    config = {
        # The name of your plugin
        'plugin_name': 'DQNMAIN',

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
        'DQNMAIN': [
            # A short usage string. This will be printed if you type HELP <name> in the BlueSky console
            'DQNMAIN argument',

            # A list of the argument types your function accepts. For a description of this, see ...
            'txt',

            # The name of your function in this plugin
            dqn_main,

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
    com_lat, com_lon, com_hdg = pu.get_centre_of_mass(ac1)

    return State(lat1, lon1, alt1, hdg1, rte1,
                 lat2, lon2, alt2, hdg2, rte2,
                 com_lat, com_lon, com_hdg)


def write_episode_info(loss: float, avg_reward: float):
    """
    This function simply keeps track of what occured during every episode, saving the actions, loss, conflicts and LoS.

    :param loss: loss from training the network
    :param avg_reward: average reward during this episode
    """

    if not SAVE_RESULTS:
        return

    workdir = os.getcwd()
    path = os.path.join(workdir, "results/training_results/")
    file = path + "training_results_com" + EXPERIMENT_NAME + ".csv"

    if not os.path.exists(path):
        os.makedirs(path)

    elapsed_time = round(time.time() - START, 2)

    epsilon = CONTROLLER.epsilon

    data = {"episode": EPISODE_COUNTER,
            "loss": loss,
            "average reward": avg_reward,
            "conflicts": N_CONFLICTS,
            "LoS": du.N_LoS,
            "instructions": N_INSTRUCTIONS,
            "action LEFT": du.N_LEFT,
            "action RIGHT": du.N_RIGHT,
            "action DIRECT": du.N_DIR,
            "action LNAV": du.N_LNAV,
            "duration": elapsed_time,
            "epsilon": epsilon
            }

    file_exists = os.path.isfile(file)

    with open(file, 'a') as f:
        headers = list(data.keys())
        writer = csv.DictWriter(f, delimiter=',', lineterminator='\n', fieldnames=headers)

        if not file_exists:
            writer.writeheader()

        writer.writerow(data)

    return


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
    global N_INSTRUCTIONS
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

                # update number of rewarded instructions
                N_INSTRUCTIONS += 1

                # TODO: do I need to remove from instructed aircraft? No right as this would be taken care of

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
    global N_INSTRUCTIONS
    global N_CONFLICTS
    global TIMER
    global START

    EPISODE_COUNTER += 1

    print("Episode {} finished".format(EPISODE_COUNTER))
    print("{} conflicts and {} losses of separation".format(N_CONFLICTS, du.N_LoS))

    # TODO: if condition met call train function after n restarts
    if EPISODE_COUNTER % TRAIN_INTERVAL == 0:
        loss = CONTROLLER.train(CONTROLLER.load_experiences())
        CONTROLLER.save_weights(name=EXPERIMENT_NAME)

        if EPISODE_COUNTER % TARGET_INTERVAL == 0:
            CONTROLLER.update_target_model()

        avg_reward = TOTAL_REWARD / N_INSTRUCTIONS
        write_episode_info(loss[0], avg_reward)
    else:
        avg_reward = TOTAL_REWARD / N_INSTRUCTIONS
        write_episode_info(None, avg_reward)

    # reset all global variables
    CONFLICTS_IN_COOLDOWN = []
    PREVIOUS_ACTIONS = []
    LoS_PAIRS = []
    TOTAL_REWARD = 0
    N_INSTRUCTIONS = 0
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
def dqn_main(argument):
    """
    I doubt we need this function. This is purely for initialization

    :param argument:
    """
    pass
