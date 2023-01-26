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

FT_NM_FACTOR = 0.000164578834   # ft * factor converts to nm
M_FT_FACTOR = 3.280839895       # m * factor converts to feet
SEP_REP_HOR = 3.5               # 3nm is min sep
SEP_REP_VER = 1500              # 1000ft is min sep
SEP_MIN_HOR = 3.0
SEP_MIN_VER = 1000

POSSIBLE_ACTIONS = {'LEFT', 'RIGHT', 'DIR', 'LNAV'}

PREVIOUS_ACTIONS = []           # buffer for previous actions with the given state and the aircraft pair


### Initialization function of your plugin. Do not change the name of this
### function, as it is the way BlueSky recognises this file as a plugin.
def init_plugin():

    # Addtional initilisation code

    # TODO: INTIALIZE REWARDS ETC. TO 0 --> DO I WANT THIS GLOBALLY OR LOCALLY

    # Configuration parameters
    config = {
        # The name of your plugin
        'plugin_name':     'TESTPLUGIN',

        # The type of this plugin. For now, only simulation plugins are possible.
        'plugin_type':     'sim',

        # Update interval in seconds. By default, your plugin's update function(s)
        # are called every timestep of the simulation. If your plugin needs less
        # frequent updates provide an update interval.
        'update_interval': 0.0,

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


def get_state_info(ac: str) -> (float, float, int, int, str, str):
    """
    This function returns all information required to build a state.

    :param ac: string of aircraft ID
    :return: lat, lon, alt, tas, current waypoint, next waypoint
    """
    idx = traf.acid.index(ac)

    cur = traf.ap.route[idx].wpname[0]
    if len(traf.ap.route[idx].wpname) > 1:
        nxt = traf.ap.route[idx].wpname[1]
    else:
        nxt = traf.ap.route[idx].wpname[0]

    return traf.lat[idx], traf.lon[idx], traf.alt[idx], traf.tas[idx], cur, nxt


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
    idx1 = traf.acid.index(ac1)
    idx2 = traf.acid.index(ac2)

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
    idx1 = traf.acid.index(ac1)
    idx2 = traf.acid.index(ac2)

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

    idx = traf.acid.index(ac)

    lat = traf.lat[idx]
    lon = traf.lon[idx]
    dest = traf.ap.dest[idx]
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


def update():
    """
    This is where the RL functionality should occur
    """

    # ------------------------------------------------------------------------------------------------------------------
    # DONE: determine possible conflicts --> add to set of pairs, ordered by proximity within pairs

    # TODO: get set of allowed actions
    # TODO: determine best action
    # TODO: eval ac of previous instructions (desire to go back to VNAV)
    # TODO: reward function
    # ------------------------------------------------------------------------------------------------------------------

    # TODO: check if instruction was given at t - 1 -> previous_experience != None
    # TODO:     reward = self.get_reward(positions, destinations, ac1, ac2) --> reward is not available before action
    # TODO:     then self.controller.store(previous_experience[idx], state) --> store this in a handy manner

    if PREVIOUS_ACTIONS:
        while PREVIOUS_ACTIONS:
            prev_state, action, ac1, ac2 = PREVIOUS_ACTIONS.pop()

            current_state = State()

    # TODO: check for new pairs
    # TODO:     then for all pairs:
    # TODO:         actions = self.controller.act(state)
    # TODO:         do actions
    # TODO:         previous_experience.append((state, actions))

    positions = {}

    # gather aircraft positions
    for acid, lat, lon, alt_m in zip(traf.id, traf.lat, traf.lon, traf.alt):
        alt = m_to_ft(alt_m)
        positions[acid] = (lat, lon, alt)

    # there is a possibility of not having any conflicts
    if not positions:
        return

    collision_pairs = get_conflict_pairs(positions)     # list of tuples
    print(collision_pairs)
    return


def reset():
    pass

### Other functions of your plugin
def testplugin(argument):
    """
     I doubt we need this function. This is purely for initialization

     :param argument:
    """
    pass
    # if '/' not in rwyname:
    #     return False, 'Argument is not a runway ' + rwyname
    # apt, rwy = rwyname.split('/RW')
    # rwy = rwy.lstrip('Y')
    # apt_thresholds = navdb.rwythresholds.get(apt)
    # if not apt_thresholds:
    #     return False, 'Argument is not a runway (airport not found) ' + apt
    # rwy_threshold = apt_thresholds.get(rwy)
    # if not rwy_threshold:
    #     return False, 'Argument is not a runway (runway not found) ' + rwy
    # # Extract runway threshold lat/lon, and runway heading
    # lat, lon, hdg = rwy_threshold
    #
    # # The ILS gate is defined as a triangular area pointed away from the runway
    # # First calculate the two far corners in cartesian coordinates
    # cone_length = 50 # nautical miles
    # cone_angle  = 20.0 # degrees
    # lat1, lon1 = geo.qdrpos(lat, lon, hdg - 180.0 + cone_angle, cone_length)
    # lat2, lon2 = geo.qdrpos(lat, lon, hdg - 180.0 - cone_angle, cone_length)
    # coordinates = np.array([lat, lon, lat1, lon1, lat2, lon2])
    # areafilter.defineArea('ILS' + rwyname, 'POLYALT', coordinates, top=4000*ft)
