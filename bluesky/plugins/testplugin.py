""" BlueSky plugin template. The text you put here will be visible
    in BlueSky as the description of your plugin. """

import os
import csv

from bluesky import stack, traf, navdb

from bluesky.plugins.atc_utils.state import State
from bluesky.plugins.atc_utils.controller import Controller
from bluesky.plugins.atc_utils import prox_util as prox


HDG_CHANGE = 45.0               # HDG change instruction deviates 15 degrees from original
TOTAL_REWARD = 0                # storage for total obtained reward this episode

EPISODE_COUNTER = 0             # counter to keep track of how many episodes have passed
EPISODE_LENGTH = 256            # THIS IS PROBABLY IRRELEVANT...
TIMER = 0                       # counter to keep track of how many update calls were made this episode
TIME_LIMIT = 1080                # 1440 updates equates to approximately 2 hours of simulation time
CONFLICT_LIMIT = 150            # This required further research!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

PREVIOUS_ACTIONS = []           # buffer for previous actions with the given state and the aircraft pair
INSTRUCTED_AIRCRAFT = []        # list of aircraft that deviated from their flightpath
CONFLICT_PAIRS = []             # buffer for current conflicts in the airspace for which instructions have been provided
COOLDOWN_LIST = []              # list containing pairs that had a loss of separation and have not parted ways yet

N_CONFLICTS = 0                 # counter for the number of conflicts that have been encountered
N_LoS = 0                       # counter for the number of separation losses
N_LEFT = 0                      # counter for the number of times action LEFT is selected
N_RIGHT = 0                     # counter for the number of times action RIGHT is selected
N_DIR = 0                       # counter for the number of times action DIR is selected
N_LNAV = 0                      # counter for the number of times action LNAV is selected

N_SKIPPED = 0

CONTROLLER = Controller()       # atc agent based on a DQN


### Initialization function of your plugin. Do not change the name of this
### function, as it is the way BlueSky recognises this file as a plugin.
def init_plugin():

    # Addtional initilisation code

    # Configuration parameters
    config = {
        # The name of your plugin
        'plugin_name':     'TESTPLUGIN',

        # The type of this plugin. For now, only simulation plugins are possible.
        'plugin_type':     'sim',

        # Update interval in seconds. By default, your plugin's update function(s)
        # are called every timestep of the simulation. If your plugin needs less
        # frequent updates provide an update interval.
        # Delta T = 0.05s in the simulation
        # NOTE: CHANGED THIS FROM 0.0
        'update_interval': 5.0,

        # The update function is called after traffic is updated. Use this if you
        # want to do things as a result of what happens in traffic. If you need to
        # something before traffic is updated please use preupdate.
        'update':          update,

        # If your plugin has a state, you will probably need a reset function to
        # clear the state in between simulations.
        'reset':         reset
        }

    stackfunctions = {
        # The command name for your function
        'TESTPLUGIN': [
            # A short usage string. This will be printed if you type HELP <name> in the BlueSky console
            'TESTPLUGIN argument',

            # A list of the argument types your function accepts. For a description of this, see ...
            'txt',

            # The name of your function in this plugin
            testplugin,

            # a longer help text of your function.
            'First test plugin to help with plugin development.']
    }

    # TODO: remove training results (or rename to other name or sth)
    # TODO: allow for running by loading best weights

    # init_plugin() should always return these two dicts.
    return config, stackfunctions


def write_csv(path: str, file: str, data: dict):
    """
    Utility function to write data to the provided file along the path.

    :param path: path to the file location
    :param file: filename
    :param data: dictionary containing the data to be written
    """
    if not os.path.exists(path):
        os.makedirs(path)

    file_exists = os.path.isfile(file)

    with open(file, 'a') as f:
        headers = list(data.keys())
        writer = csv.DictWriter(f, delimiter=',', lineterminator='\n', fieldnames=headers)

        if not file_exists:
            writer.writeheader()

        writer.writerow(data)


def get_next_two_waypoints(idx: int) -> (str, str):
    """
    Function that returns the next two waypoints of an aircraft, or doubles the only waypoint if there is just one.

    :param idx: index of the aircraft
    :return:
    """
    if not traf.ap.route[idx].wpname:
        # TODO: remove this temporary fix when up and running!
        return "EH007", "EH007"
    else:
        cur = traf.ap.route[idx].wpname[0]

    if len(traf.ap.route[idx].wpname) > 1:
        nxt = traf.ap.route[idx].wpname[1]
    else:
        nxt = traf.ap.route[idx].wpname[0]

    return cur, nxt


def load_state_data(ac: str) -> (float, float, int, int, int, int, int):
    """
    This function gathers all data from one single aircraft that are required for a state definition.

    :param ac: string containing aircraft id
    :return: tuple of all data for one aircraft's state
    """
    idx = traf.id.index(ac)

    lat = traf.lat[idx]
    lon = traf.lon[idx]
    alt = traf.alt[idx]
    tas = traf.tas[idx]
    hdg = traf.hdg[idx]

    cur_id, nxt_id = get_next_two_waypoints(idx)
    cur = navdb.getwpidx(cur_id)
    nxt = navdb.getwpidx(nxt_id)

    return lat, lon, alt, tas, hdg, cur, nxt


def get_current_state(ac1: str, ac2: str) -> State:
    """
    This function returns all information required to build a state.

    :param ac1: string of aircraft 1's ID
    :param ac2: string of aircraft 2's ID
    :return: current state given the two aircraft
    """

    lat1, lon1, alt1, tas1, hdg1, cur1, nxt1 = load_state_data(ac1)
    lat2, lon2, alt2, tas2, hdg2, cur2, nxt2 = load_state_data(ac2)

    return State(lat1, lon1, alt1, tas1, hdg1, cur1, nxt1,
                 lat2, lon2, alt2, tas2, hdg2, cur2, nxt2)


def has_reached_goal(ac: str) -> bool:
    """
    This function determines when an aircraft has reached its goal position (the last waypoint in its route).

    :param ac: aircraft in question
    :return: boolean of reached goal status
    """

    idx = traf.id.index(ac)

    lat = traf.lat[idx]
    lon = traf.lon[idx]
    dest = traf.ap.dest[idx]

    if dest == "":
        print(f"{ac} has no destination defined")
        return False

    # destination = "EH007"
    wplat = navdb.wplat[navdb.wpid.index(dest)]
    wplon = navdb.wplon[navdb.wpid.index(dest)]

    if wplat == lat and wplon == lon:
        return True
    else:
        return False


def get_reward(ac1: str, ac2: str) -> int:
    """
    This function returns the reward obtained from the action that was taken.

    :param ac1: first aircraft in the conflict
    :param ac2: second aircraft in the conflict
    :return: integer reward
    """

    global N_LoS

    # TODO: make more complex
    if prox.is_loss_of_separation(ac1, ac2):
        N_LoS += 1
        return -1
    elif has_reached_goal(ac1) or has_reached_goal(ac2):
        return 1
    else:
        return 0


def engage_lnav(ac: str):
    stack.stack(f"LNAV {ac} ON")
    stack.stack(f"VNAV {ac} ON")
    return


def direct_to_wpt(ac: str, wpt: str):
    stack.stack(f"LNAV {ac} ON")
    stack.stack(f"DIRECT {ac} {wpt}")
    stack.stack(f"VNAV {ac} ON")
    return


def change_heading(ac: str, right: bool):
    """
    This function alters the heading of an aircraft by HDG_CHANGE degrees, keeping between 0 and 360 degrees.

    :param ac: aircraft id string
    :param right: boolean that is true when a right turn is required
    """
    if right:
        hdg_change = HDG_CHANGE
    else:
        hdg_change = -1 * HDG_CHANGE

    current_hdg = traf.hdg[traf.id.index(ac)]

    hdg = (current_hdg + hdg_change) % 360

    stack.stack(f"HDG {ac} {hdg}")
    return


def handle_instruction(ac: str, action: str, wpt: str = None):
    """
    This function checks what instruction was given and calls the appropriate functions to handle these instructions.

    :param ac: aircraft id of aircraft that was given an instruction
    :param action: action that needs to be taken
    :param wpt: possible waypoint if a DIR instruction is given
    """

    global N_LEFT
    global N_RIGHT
    global N_DIR
    global N_LNAV

    workdir = os.getcwd()
    path = os.path.join(workdir, "results/instructions/")
    file = path + "training_instructions.csv"

    data = {"episode": EPISODE_COUNTER, "aircraft": ac, "instruction": action}

    write_csv(path, file, data)

    if action == "HDG_L":
        N_LEFT += 1
        change_heading(ac, False)
        # INSTRUCTED_AIRCRAFT.append(ac)
    elif action == "HDG_R":
        N_RIGHT += 1
        change_heading(ac, True)
        # INSTRUCTED_AIRCRAFT.append(ac)
    elif action == "DIR":
        N_DIR += 1
        direct_to_wpt(ac, wpt)
    elif action == "LNAV":
        N_LNAV += 1
        engage_lnav(ac)


def write_episode_info(loss: float, avg_reward: float):
    """
    This function simply keeps track of what occured during every episode, saving the actions, loss, conflicts and LoS.

    :param loss: loss from training the network
    :param avg_reward: average reward during this episode
    """

    workdir = os.getcwd()
    path = os.path.join(workdir, "results/training_results/")
    file = path + "training_results.csv"

    data = {"episode":          EPISODE_COUNTER,
            "loss":             loss,
            "average reward":   avg_reward,
            "conflicts":        N_CONFLICTS,
            "LoS":              N_LoS,
            "Skipped":          N_SKIPPED,
            "action LEFT":      N_LEFT,
            "action RIGHT":     N_RIGHT,
            "action DIRECT":    N_DIR,
            "action LNAV":      N_LNAV,
            }

    write_csv(path, file, data)

    return


def get_previous_action_info(ac1: str, ac2: str) -> (State, str, str, str, str):
    """
    This function returns the previous state, the actions for both aircraft and the aircraft themselves.

    :param ac1: string of first aircraft id
    :param ac2: string of second aircraft id
    :return: previous State, action of ac1, action of ac2, ac1 and ac2
    """

    # find the previous action that is relevant for these two aircraft
    previous_action = [prev_act for prev_act in PREVIOUS_ACTIONS if ac1 in prev_act and ac2 in prev_act]

    # if this is not exactly one action, then an error has occurred
    if len(previous_action) != 1:
        raise Exception("Found more than one previous action for this conflict pair {} and {}".format(ac1, ac2))

    # remove the action from the global list
    prev_state, action1, action2, ac1, ac2 = previous_action[0]
    PREVIOUS_ACTIONS.remove((prev_state, action1, action2, ac1, ac2))

    return prev_state, action1, action2, ac1, ac2


def store_experience(ac1: str, ac2: str):
    """
    This function stores the experiences once a conflict has been resolved or has ended in a loss of separation.

    :param ac1: string containing aircraft 1
    :param ac2: string containing aircraft 2
    """

    global TOTAL_REWARD

    # find the previous action information that is relevant for these two aircraft
    prev_state, action1, action2, ac1, ac2 = get_previous_action_info(ac1, ac2)

    # if one of the aircraft was removed, we disregard this case as we cannot construct a state
    if ac1 in traf.id and ac2 in traf.id:
        current_state = get_current_state(ac1, ac2)

        # the reward is based on the current state, so can be taken directly from info of the simulator
        reward = get_reward(ac1, ac2)
        TOTAL_REWARD += reward

        CONTROLLER.store_experiences(prev_state, action1, action2, reward, current_state)
    else:
        print("{} or {} has despawned".format(ac1, ac2))

    return


def update():
    """
    This is where the RL functionality should occur
    """
    print("\n")

    # ------------------------------------------------------------------------------------------------------------------
    # TODO: get set of allowed actions (are there actions that are perhaps illegal?)
    # TODO: reward function needs to be made more complex
    # ------------------------------------------------------------------------------------------------------------------

    global TIMER
    global TOTAL_REWARD
    global N_CONFLICTS
    global N_SKIPPED

    TIMER = TIMER + 1

    if TIMER == TIME_LIMIT or N_CONFLICTS >= CONFLICT_LIMIT:
        stack.stack("RESET")
        return

    # first check if an instruction was given at t - 1, then the experience buffer needs to be updated
    # if PREVIOUS_ACTIONS:
    #     while PREVIOUS_ACTIONS:
    #         prev_state, action1, action2, ac1, ac2 = PREVIOUS_ACTIONS.pop()
    #
    #         # DONE: what if ac despawned? --> currently we remove this case
    #         if ac1 in traf.id and ac2 in traf.id:
    #             current_state = get_current_state(ac1, ac2)
    #
    #             # the reward is based on the current state, so can be taken directly from info of the simulator
    #             reward = get_reward(ac1, ac2)
    #             TOTAL_REWARD += reward
    #
    #             CONTROLLER.store_experiences(prev_state, action1, action2, reward, current_state)

    positions = {}

    # gather aircraft positions
    for acid, lat, lon, alt_m in zip(traf.id, traf.lat, traf.lon, traf.alt):
        alt = prox.m_to_ft(alt_m)
        positions[acid] = (lat, lon, alt)

    # there is a possibility of not having any aircraft
    if not positions:
        return

    current_conflict_pairs = prox.get_conflict_pairs(positions)     # list of tuples

    print("current conflict pairs: {}".format(current_conflict_pairs))
    print("registered conflict pairs: {}".format(CONFLICT_PAIRS))

    for ac1, ac2 in COOLDOWN_LIST:
        if (ac1, ac2) not in current_conflict_pairs and (ac2, ac1) not in current_conflict_pairs:
            COOLDOWN_LIST.remove((ac1, ac2))
            print("removing {} and {} from cooldown list".format(ac1, ac2))

    print("registered cooldown pairs: {}".format(COOLDOWN_LIST))

    # first determine if there are new conflict pairs, and give these pairs an instruction
    for ac1, ac2 in current_conflict_pairs:
        # the pair cannot already be in the conflict pairs list and also not be in the cooldown list due to an LoS
        if (ac1, ac2) not in CONFLICT_PAIRS and (ac1, ac2) not in COOLDOWN_LIST \
                and (ac2, ac1) not in CONFLICT_PAIRS and (ac2, ac1) not in COOLDOWN_LIST:
            print("instructing ({}, {})".format(ac1, ac2))

            CONFLICT_PAIRS.append((ac1, ac2))
            current_state = get_current_state(ac1, ac2)
            action1, action2 = CONTROLLER.act(current_state)

            # waypoint in state is the index of its id in the navdb
            handle_instruction(ac1, action1, navdb.wpid[current_state.get_next_waypoint(1)])
            handle_instruction(ac2, action2, navdb.wpid[current_state.get_next_waypoint(2)])

            PREVIOUS_ACTIONS.append((current_state, action1, action2, ac1, ac2))

            N_CONFLICTS += 1
        else:
            N_SKIPPED += 1

    # check LoS or clear from conflict, then we can store the experience and resume original navigation
    for ac1, ac2 in CONFLICT_PAIRS:
        if ac1 not in traf.id or ac2 not in traf.id:
            # if the one or both aircraft have been removed from the simulation, remove them from the conflict pairs
            CONFLICT_PAIRS.remove((ac1, ac2))
            # and remove them from the action list
            _ = get_previous_action_info(ac1, ac2)
        elif prox.is_loss_of_separation(ac1, ac2):
            print("removing ({}, {}) due to a loss of separation".format(ac1, ac2))
            CONFLICT_PAIRS.remove((ac1, ac2))
            COOLDOWN_LIST.append((ac1, ac2))

            # store experience
            store_experience(ac1, ac2)

            # resume own navigation
            engage_lnav(ac1)
            print("{} is resuming own navigation!".format(ac1))
            engage_lnav(ac2)
            print("{} is resuming own navigation!".format(ac2))
        elif (ac1, ac2) not in current_conflict_pairs and (ac2, ac1) not in current_conflict_pairs:
            print("removing ({}, {})".format(ac1, ac2))
            CONFLICT_PAIRS.remove((ac1, ac2))

            # store experience
            store_experience(ac1, ac2)

            # resume own navigation
            engage_lnav(ac1)
            print("{} is resuming own navigation!".format(ac1))
            engage_lnav(ac2)
            print("{} is resuming own navigation!".format(ac2))

    # additional check for not in traf.id but in CONFLICT_PAIRS and PREVIOUS ACTIONS?
    #           --> is this where the goal is reached?

    # resume_navigation(collision_pairs)
    #
    # # there is a possibility of not having any conflicts
    # if not collision_pairs:
    #     return
    #
    # # give instructions to the aircraft and save the state, actions and corresponding aircraft id's
    # for ac1, ac2 in collision_pairs:
    #     current_state = get_current_state(ac1, ac2)
    #
    #     action1, action2 = CONTROLLER.act(current_state)
    #
    #     # waypoint in state is the index of its id in the navdb
    #     handle_instruction(ac1, action1, navdb.wpid[current_state.get_next_waypoint(1)])
    #     handle_instruction(ac2, action2, navdb.wpid[current_state.get_next_waypoint(2)])
    #
    #     PREVIOUS_ACTIONS.append((current_state, action1, action2, ac1, ac2))
    #
    # return


def reset():
    """
    Reset after episode has finished.
    """

    print("resetting main plugin")

    # global INSTRUCTED_AIRCRAFT
    global PREVIOUS_ACTIONS
    global EPISODE_COUNTER
    global CONFLICT_PAIRS
    global COOLDOWN_LIST
    global TOTAL_REWARD
    global N_CONFLICTS
    global N_LoS
    global N_LEFT
    global N_RIGHT
    global N_DIR
    global N_LNAV
    global TIMER

    global N_SKIPPED

    EPISODE_COUNTER += 1

    # TODO: if condition met call train function after n restarts
    loss = CONTROLLER.train(CONTROLLER.load_experiences())
    print("Episode {} finished".format(EPISODE_COUNTER))
    print("Skipped {} conflicts due to earlier given instructions\n".format(N_SKIPPED))
    CONTROLLER.save_weights()

    avg_reward = TOTAL_REWARD / N_CONFLICTS
    write_episode_info(loss[0], avg_reward)

    # reset all global variables
    # INSTRUCTED_AIRCRAFT = []
    PREVIOUS_ACTIONS = []
    CONFLICT_PAIRS = []
    COOLDOWN_LIST = []
    TOTAL_REWARD = 0
    N_CONFLICTS = 0
    N_SKIPPED = 0
    N_LoS = 0
    N_LEFT = 0
    N_RIGHT = 0
    N_DIR = 0
    N_LNAV = 0
    TIMER = 0

    # TODO: fix this....
    if EPISODE_COUNTER == EPISODE_LENGTH:
        stack.stack("STOP")

    stack.stack("TAXI ON")
    stack.stack("FF")

    return


### Other functions of your plugin
def testplugin(argument):
    """
     I doubt we need this function. This is purely for initialization

     :param argument:
    """
    pass
