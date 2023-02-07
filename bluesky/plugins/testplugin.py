""" BlueSky plugin template. The text you put here will be visible
    in BlueSky as the description of your plugin. """

import numpy as np
from math import sqrt

# Import the global bluesky objects. Uncomment the ones you need
from bluesky import stack, traf  #, settings, navdb, sim, scr, tools
from bluesky import navdb
from bluesky.tools.aero import ft
from bluesky.tools import geo, areafilter

from bluesky.plugins.atc_utils.state import State
from bluesky.plugins.atc_utils.controller import Controller

FT_NM_FACTOR = 0.000164578834   # ft * factor converts to nm
M_FT_FACTOR = 3.280839895       # m * factor converts to feet
SEP_REP_HOR = 3.5               # report within 3.5 nm
SEP_REP_VER = 1500              # report within 1500 ft
SEP_MIN_HOR = 3.0               # 3 nm is min sep
SEP_MIN_VER = 1000              # 1000 ft is min sep
HDG_CHANGE = 15.0               # HDG change instruction deviates 15 degrees from original

EPISODE_COUNTER = 0             # counter to keep track of how many episodes have passed
EPISODE_LIMIT = 140           # 14400 updates equates to approximately 2 hours of simulation time
TIMER = 0                       # counter to keep track of how many update calls were made this episode

PREVIOUS_ACTIONS = []           # buffer for previous actions with the given state and the aircraft pair

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

    # init_plugin() should always return these two dicts.
    return config, stackfunctions


### Periodic update functions that are called by the simulation. You can replace
### this by anything, so long as you communicate this in init_plugin

def m_to_ft(alt: int) -> int:
    return int(alt * M_FT_FACTOR)


def ft_to_nm(alt: int) -> float:
    return alt * FT_NM_FACTOR


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


def get_current_state(ac1: str, ac2: str) -> State:
    """
    This function returns all information required to build a state.

    :param ac1: string of aircraft 1's ID
    :param ac2: string of aircraft 2's ID
    :return: current state given the two aircraft
    """
    idx1 = traf.id.index(ac1)
    idx2 = traf.id.index(ac2)

    cur1_id, nxt1_id = get_next_two_waypoints(idx1)
    cur2_id, nxt2_id = get_next_two_waypoints(idx2)

    # convert waypoints to their indices in the navigation database
    cur1 = navdb.wpid.index(cur1_id)
    nxt1 = navdb.wpid.index(nxt1_id)
    cur2 = navdb.wpid.index(cur2_id)
    nxt2 = navdb.wpid.index(nxt2_id)

    current_state = State(
        traf.lat[idx1], traf.lon[idx1], traf.alt[idx1], traf.tas[idx1], cur1, nxt1,
        traf.lat[idx2], traf.lon[idx2], traf.alt[idx2], traf.tas[idx2], cur2, nxt2
    )

    return current_state


def within_stated_area(lat1: float, lat2: float, lon1: float, lon2: float,
                       alt1: int, alt2: int, h_lim: float, v_lim: int) -> bool:
    """
    This function returns true when two aircraft are within the stated area.

    :param lat1: ac1 latitude
    :param lat2: ac2 latitude
    :param lon1: ac1 longitude
    :param lon2: ac2 longitude
    :param alt1: ac1 altitude
    :param alt2: ac2 altitude
    :param h_lim: horizontal limit
    :param v_lim: vertical limit
    :return: boolean of within limits
    """
    _, dist_h = geo.qdrdist(lat1, lon1, lat2, lon2)  # bearing, distance (nm)
    dist_v = abs(alt1 - alt2)

    if dist_h <= h_lim and dist_v <= v_lim:
        return True
    else:
        return False


def is_within_alert_distance(ac1: str, ac2: str) -> bool:
    """
    This function returns a boolean indicating whether two aircraft are within the notification area.

    :param ac1: id of aircraft 1
    :param ac2: id of aircraft 2
    :return: boolean for a loss of separation
    """
    idx1 = traf.id.index(ac1)
    idx2 = traf.id.index(ac2)

    lat1 = traf.lat[idx1]
    lat2 = traf.lat[idx2]
    lon1 = traf.lon[idx1]
    lon2 = traf.lon[idx2]
    alt1 = traf.alt[idx1]
    alt2 = traf.alt[idx2]

    return within_stated_area(lat1, lat2, lon1, lon2, alt1, alt2, SEP_REP_HOR, SEP_REP_VER)


def is_loss_of_separation(ac1: str, ac2: str) -> bool:
    """
    This function returns a boolean indicating whether a loss of separation has occurred.

    :param ac1: id of aircraft 1
    :param ac2: id of aircraft 2
    :return: boolean for a loss of separation
    """
    idx1 = traf.id.index(ac1)
    idx2 = traf.id.index(ac2)

    lat1 = traf.lat[idx1]
    lat2 = traf.lat[idx2]
    lon1 = traf.lon[idx1]
    lon2 = traf.lon[idx2]
    alt1 = traf.alt[idx1]
    alt2 = traf.alt[idx2]

    return within_stated_area(lat1, lat2, lon1, lon2, alt1, alt2, SEP_MIN_HOR, SEP_MIN_VER)


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


def direct_distance(hor: float, ver: int) -> float:
    """
    Using the Pythagorean Theorem, the straight-line distance is computed based on the horizontal and vertical distance.

    :param hor: horizontal distance [nm]
    :param ver: vertical distance [ft]
    :return: distance [nm]
    """

    return sqrt(hor ** 2 + ft_to_nm(ver) ** 2)


def get_reward(ac1: str, ac2: str) -> int:
    """
    This function returns the reward obtained from the action that was taken.

    :param ac1: first aircraft in the conflict
    :param ac2: second aircraft in the conflict
    :return: integer reward
    """
    # TODO: make more complex
    if is_loss_of_separation(ac1, ac2):
        return -1
    elif has_reached_goal(ac1) or has_reached_goal(ac2):
        return 1
    else:
        return 0


def get_conflict_pairs(position_list: dict) -> list[tuple[str, str]]:
    """
    This functions returns a list of pairs that are nearing minimum separation.

    :param position_list: Dictionary containing all present aircraft, along with their positions
    :return: list of aircraft ID pairs (strings)
    """

    conflict_list = []
    conflict_dist = []
    all_pairs = [(a, b) for idx, a in enumerate(list(position_list.keys())) for b in list(position_list.keys())[idx+1:]]

    for a, b in all_pairs:
        lat_a, lon_a, alt_a = position_list[a]
        lat_b, lon_b, alt_b = position_list[b]

        _, dist_h = geo.qdrdist(lat_a, lon_a, lat_b, lon_b)   # bearing, distance (nm)
        dist_v = abs(alt_a - alt_b)

        # distance checks out, bearing is weird
        # print(f"Distance between {a} and {b} is {dist_h}nm horizontally and {dist_v}ft vertically.")

        if dist_h < SEP_REP_HOR and dist_v < SEP_REP_VER:
            print(f"{a} and {b} are within the notification range of each other")
            conflict_list.append((str(a), str(b)))
            conflict_dist.append(direct_distance(dist_h, dist_v))

    sorted_conflicts = [x for _, x in sorted(zip(conflict_dist, conflict_list))]

    return sorted_conflicts


def engage_lnav(ac: str):
    stack.stack(f"LNAV {ac} ON")
    return


def direct_to_wpt(ac: str, wpt: str):
    stack.stack(f"DIRECT {ac} {wpt}")
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
    This function checks what instruction was given and calls the appropriate functions to handle these instrucitons.

    :param ac: aircraft id of aircraft that was given an instruction
    :param action: action that needs to be taken
    :param wpt: possible waypoint if a DIR instruction is given
    """
    if action == "HDG_L":
        change_heading(ac, False)
    elif action == "HDG_R":
        change_heading(ac, True)
    elif action == "DIR":
        direct_to_wpt(ac, wpt)
    elif action == "LNAV":
        engage_lnav(ac)


def update():
    """
    This is where the RL functionality should occur
    """

    # ------------------------------------------------------------------------------------------------------------------
    # DONE: determine possible conflicts --> add to set of pairs, ordered by proximity within pairs

    # TODO: get set of allowed actions
    # TODO: determine best action
    # TODO: handle aircraft that were given previous instructions (desire to go back to LNAV)
    # TODO: reward function needs to be made more complex
    # ------------------------------------------------------------------------------------------------------------------

    # DONE: check if instruction was given at t - 1 -> previous_experience != None
    # DONE:     reward = self.get_reward(positions, destinations, ac1, ac2) --> reward is not available before action
    # DONE:     then self.controller.store(previous_experience[idx], state) --> store this in a handy manner

    global TIMER
    TIMER = TIMER + 1

    if EPISODE_COUNTER == EPISODE_LIMIT or TIMER == EPISODE_LIMIT:
        reset()

    # first check if an instruction was given at t - 1, then the experience buffer needs to be updated
    if PREVIOUS_ACTIONS:
        while PREVIOUS_ACTIONS:
            prev_state, action1, action2, ac1, ac2 = PREVIOUS_ACTIONS.pop()

            current_state = get_current_state(ac1, ac2)

            # the reward is based on the current state, so can be taken directly from info of the simulator
            reward = get_reward(ac1, ac2)

            CONTROLLER.store_experiences(prev_state, action1, action2, reward, current_state)

    # DONE: check for new pairs
    # DONE:     then for all pairs:
    # DONE:         actions = self.controller.act(state)
    # DONE:         do actions
    # DONE:         previous_experience.append((state, actions, aircraft))

    # TODO: add check when to reset --> after x timesteps
    # TODO: add reset call after condition

    positions = {}

    # gather aircraft positions
    for acid, lat, lon, alt_m in zip(traf.id, traf.lat, traf.lon, traf.alt):
        alt = m_to_ft(alt_m)
        positions[acid] = (lat, lon, alt)

    # there is a possibility of not having any aircraft
    if not positions:
        return

    collision_pairs = get_conflict_pairs(positions)     # list of tuples

    # there is a possibility of not having any conflicts
    if not collision_pairs:
        return

    # give instructions to the aircraft and save the state, actions and corresponding aircraft id's
    for ac1, ac2 in collision_pairs:
        current_state = get_current_state(ac1, ac2)

        action1, action2 = CONTROLLER.act(current_state)

        handle_instruction(ac1, action1, current_state.get_next_waypoint(1))
        handle_instruction(ac2, action2, current_state.get_next_waypoint(2))

        PREVIOUS_ACTIONS.append((current_state, action1, action2, ac1, ac2))

    return


def reset():
    """
    Reset after episode has finished.
    """
    global EPISODE_COUNTER
    global TIMER
    EPISODE_COUNTER += 1
    TIMER = 0

    # TODO: if condition met call train function after n restarts
    loss = CONTROLLER.train(CONTROLLER.load_experiences())
    CONTROLLER.save_weights()

    # reload the scenario --> does this work with keeping track of buffer? THIS WORKS
    stack.stack('IC testplugin.scn')

    return

### Other functions of your plugin
def testplugin(argument):
    """
     I doubt we need this function. This is purely for initialization

     :param argument:
    """
    pass
