""" BlueSky plugin template. The text you put here will be visible
    in BlueSky as the description of your plugin. """

import os
import csv
import time

# Import the global bluesky objects. Uncomment the ones you need
from bluesky import stack, traf, navdb  #, settings, sim, scr, tools
from bluesky.tools.aero import ft
from bluesky.tools import geo, areafilter

from bluesky.plugins.atc_utils.state import State
from bluesky.plugins.atc_utils.controller import Controller
from bluesky.plugins.atc_utils import prox_util as pu


HDG_CHANGE = 15.0               # HDG change instruction deviates 15 degrees from original
TOTAL_REWARD = 0                # storage for total obtained reward this episode

EPISODE_COUNTER = 0             # counter to keep track of how many episodes have passed
EPISODE_LIMIT = 1000            # limits the amount of episodes
START = 0                       # start time
TIMER = 0                       # counter to keep track of how many update calls were made this episode
TIME_LIMIT = 720                # 1440 updates equates to approximately 2 hours of simulation time
CONFLICT_LIMIT = 100            # NOTE: rather randomly selected

PREVIOUS_ACTIONS = []           # buffer for previous actions with the given state and the aircraft pair
INSTRUCTED_AIRCRAFT = []        # list of aircraft that deviated from their flightpath
CONFLICT_PAIRS = []             # list of aircraft that are currently in conflict with one another
LoS_PAIRS = []                  # list of aircraft that have currently lost separation

N_CONFLICTS = 0                 # counter for the number of conflicts that have been encountered
N_LoS = 0                       # counter for the number of separation losses
N_LEFT = 0                      # counter for the number of times action LEFT is selected
N_RIGHT = 0                     # counter for the number of times action RIGHT is selected
N_DIR = 0                       # counter for the number of times action DIR is selected
N_LNAV = 0                      # counter for the number of times action LNAV is selected

ROUTES = {"A": 1, "R": 2, "S": 3}

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


def load_state_data(ac: str) -> (float, float, int, int, int):
    """
    This function gathers all data from one single aircraft that are required for a state definition.

    :param ac: string containing aircraft id
    :return: tuple of all data for one aircraft's state
    """
    idx = traf.id.index(ac)

    lat = traf.lat[idx]
    lon = traf.lon[idx]
    alt = traf.alt[idx]
    hdg = traf.hdg[idx]

    # the route of an aircraft is defined by the last letter in its id
    rte = ROUTES[ac[-1]]

    return lat, lon, alt, hdg, rte


def get_current_state(ac1: str, ac2: str) -> State:
    """
    This function returns all information required to build a state.

    :param ac1: string of aircraft 1's ID
    :param ac2: string of aircraft 2's ID
    :return: current state given the two aircraft
    """

    lat1, lon1, alt1, hdg1, rte1 = load_state_data(ac1)
    lat2, lon2, alt2, hdg2, rte2 = load_state_data(ac2)
    com_lat, com_lon, com_hdg = pu.get_centre_of_mass(ac1)

    return State(lat1, lon1, alt1, hdg1, rte1,
                 lat2, lon2, alt2, hdg2, rte2,
                 com_lat, com_lon, com_hdg)


def has_reached_goal(ac: str) -> bool:
    """
    This function determines when an aircraft has reached its goal position (the last waypoint in its route).

    :param ac: aircraft in question
    :return: boolean of reached goal status
    """

    # TODO: is this still necessary?

    idx = traf.id.index(ac)

    lat = traf.lat[idx]
    lon = traf.lon[idx]
    dest = traf.ap.dest[idx]

    if dest == "":
        # print(f"{ac} has no destination defined")
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
    if pu.is_loss_of_separation(ac1, ac2):
        return -1
    elif not pu.is_within_alert_distance(ac1, ac2):
        return 1
    # TODO: more rewards with larger distance (max = conflict border?)
    else:
        dist_ac = pu.get_distance_to_ac(ac1, ac2)
        dist_alert = pu.get_distance_to_alert_border()
        return min(1, dist_ac/dist_alert)


def engage_lnav(ac: str):
    stack.stack(f"LNAV {ac} ON")
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

    if action == "HDG_L":
        N_LEFT += 1
        change_heading(ac, False)
        INSTRUCTED_AIRCRAFT.append(ac)
    elif action == "HDG_R":
        N_RIGHT += 1
        change_heading(ac, True)
        INSTRUCTED_AIRCRAFT.append(ac)
    # elif action == "DIR":
    #     N_DIR += 1
    #     direct_to_wpt(ac, wpt)
    elif action == "LNAV":
        # print("{} is resuming LNAV with flightplan {}".format(ac, traf.ap.route[traf.id.index(ac)].wpname))
        N_LNAV += 1
        engage_lnav(ac)


def resume_navigation(collision_pairs):
    """
    This function checks whether aircraft that received a heading change are allowed to resume their own navigation.
    """

    global INSTRUCTED_AIRCRAFT

    for ac in INSTRUCTED_AIRCRAFT:
        if not [pair for pair in collision_pairs if ac in pair] and ac in traf.id:
            # print("{} is resuming own navigation!".format(ac))
            engage_lnav(ac)

    INSTRUCTED_AIRCRAFT = []

    return


def write_episode_info(loss: float, avg_reward: float):
    """
    This function simply keeps track of what occured during every episode, saving the actions, loss, conflicts and LoS.

    :param loss: loss from training the network
    :param avg_reward: average reward during this episode
    """

    workdir = os.getcwd()
    path = os.path.join(workdir, "results/training_results/")
    file = path + "training_results_mse_exploration.csv"

    if not os.path.exists(path):
        os.makedirs(path)

    elapsed_time = round(time.time() - START, 2)

    epsilon = CONTROLLER.epsilon

    data = {"episode":          EPISODE_COUNTER,
            "loss":             loss,
            "average reward":   avg_reward,
            "conflicts":        N_CONFLICTS,
            "LoS":              N_LoS,
            "action LEFT":      N_LEFT,
            "action RIGHT":     N_RIGHT,
            "action DIRECT":    N_DIR,
            "action LNAV":      N_LNAV,
            "duration":         elapsed_time,
            "epsilon":          epsilon
            }

    file_exists = os.path.isfile(file)

    with open(file, 'a') as f:
        headers = list(data.keys())
        writer = csv.DictWriter(f, delimiter=',', lineterminator='\n', fieldnames=headers)

        if not file_exists:
            writer.writeheader()

        writer.writerow(data)

    return


def update():
    """
    This is the main function of the plugin, which is called each update.
    """

    # ------------------------------------------------------------------------------------------------------------------
    # DONE: compute centre of mass and average heading
    # DONE: redefine state space
    # TODO: give action for single plane for only closest conflict
    # TODO: increase action space to also do nothing?
    # TODO: give reward based on distance to conflict --> the further the better
    # TODO: start with just two transitions
    # DONE: register route number
    # DONE: get_current_state
    # DONE: handle_instructions
    # ------------------------------------------------------------------------------------------------------------------

    global TIMER
    global START
    global TOTAL_REWARD
    global N_CONFLICTS
    global N_LoS

    if TIMER == 0:
        print("Plugin reset finished at: {}".format(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))))
        START = time.time()

    TIMER = TIMER + 1

    if TIMER == TIME_LIMIT or N_CONFLICTS >= CONFLICT_LIMIT:
        stack.stack("RESET")
        return

    # first check if an instruction was given at t - 1, then the experience buffer needs to be updated
    if PREVIOUS_ACTIONS:
        while PREVIOUS_ACTIONS:
            prev_state, action, ac1, ac2 = PREVIOUS_ACTIONS.pop()

            if ac1 in traf.id and ac2 in traf.id:
                current_state = get_current_state(ac1, ac2)

                # the reward is based on the current state, so can be taken directly from info of the simulator
                reward = get_reward(ac1, ac2)
                TOTAL_REWARD += reward

                CONTROLLER.store_experiences(prev_state, action, reward, current_state)

    positions = {}

    # gather aircraft positions
    for acid, lat, lon, alt_m in zip(traf.id, traf.lat, traf.lon, traf.alt):
        alt = pu.m_to_ft(alt_m)
        positions[acid] = (lat, lon, alt)  # alt in ft

    # there is a possibility of not having any aircraft
    if not positions:
        return

    # TODO: FIX THIS TO HAVE CONFLICTS FOR BOTH AC
    current_conflict_pairs = pu.get_conflict_pairs(positions)     # list of tuples

    # remove old conflict pairs that are no longer in conflict
    for (ac1, ac2) in CONFLICT_PAIRS:
        if (ac1, ac2) not in current_conflict_pairs and (ac2, ac1) not in current_conflict_pairs:
            CONFLICT_PAIRS.remove((ac1, ac2))

    # remove old LoS pairs that are no longer in LoS
    for (ac1, ac2) in LoS_PAIRS:
        if not pu.is_loss_of_separation(ac1, ac2):
            LoS_PAIRS.remove((ac1, ac2))

    # add new collision pairs to conflict pairs and new LoS pairs to stored pairs
    for (ac1, ac2) in current_conflict_pairs:
        if (ac1, ac2) not in CONFLICT_PAIRS and (ac2, ac1) not in CONFLICT_PAIRS:
            CONFLICT_PAIRS.append((ac1, ac2))
            N_CONFLICTS += 1
        if pu.is_loss_of_separation(ac1, ac2) and (ac1, ac2) not in LoS_PAIRS and (ac2, ac1) not in LoS_PAIRS:
            LoS_PAIRS.append((ac1, ac2))
            N_LoS += 1
            
    # TODO: is this correct
    resume_navigation(current_conflict_pairs)

    # there is a possibility of not having any conflicts
    if not current_conflict_pairs:
        return

    # give instructions to the aircraft and save the state, actions and corresponding aircraft id's
    for ac1, ac2 in current_conflict_pairs:
        current_state = get_current_state(ac1, ac2)

        action1, action2 = CONTROLLER.act(current_state)

        # waypoint in state is the index of its id in the navdb
        handle_instruction(ac1, action1)
        handle_instruction(ac2, action2)

        PREVIOUS_ACTIONS.append((current_state, action1, ac1, ac2))

    return


def reset():
    """
    Reset after episode has finished.
    """

    print("Plugin reset at: {}".format(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))))

    print("resetting main plugin")
    global INSTRUCTED_AIRCRAFT
    global PREVIOUS_ACTIONS
    global CONFLICT_PAIRS
    global LoS_PAIRS

    global EPISODE_COUNTER
    global TOTAL_REWARD
    global N_CONFLICTS
    global N_LoS
    global N_LEFT
    global N_RIGHT
    global N_DIR
    global N_LNAV
    global TIMER
    global START

    EPISODE_COUNTER += 1

    print("Episode {} finished".format(EPISODE_COUNTER))

    # TODO: if condition met call train function after n restarts
    if EPISODE_COUNTER % 4 == 0:
        loss = CONTROLLER.train(CONTROLLER.load_experiences())
        CONTROLLER.save_weights()

        if EPISODE_COUNTER % 8 == 0:
            CONTROLLER.update_target_model()

        avg_reward = TOTAL_REWARD / (N_LEFT + N_RIGHT + N_DIR + N_LNAV)
        write_episode_info(loss[0], avg_reward)
    else:
        avg_reward = TOTAL_REWARD / (N_LEFT + N_RIGHT + N_DIR + N_LNAV)
        write_episode_info(None, avg_reward)

    # reset all global variables
    INSTRUCTED_AIRCRAFT = []
    PREVIOUS_ACTIONS = []
    CONFLICT_PAIRS = []
    LoS_PAIRS = []

    TOTAL_REWARD = 0
    N_CONFLICTS = 0
    N_LoS = 0
    N_LEFT = 0
    N_RIGHT = 0
    N_DIR = 0
    N_LNAV = 0
    TIMER = 0
    START = 0

    if EPISODE_COUNTER == EPISODE_LIMIT:
        # TODO: make graphs of results
        print("Reached stopping condition")
        print("Epsilons: {}".format(CONTROLLER.epsilons))
        stack.stack("STOP")

    stack.stack("TAXI OFF")
    stack.stack("FF")

    return


### Other functions of your plugin
def testplugin(argument):
    """
     I doubt we need this function. This is purely for initialization

     :param argument:
    """
    pass
