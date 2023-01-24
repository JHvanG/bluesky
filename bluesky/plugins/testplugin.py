""" BlueSky plugin template. The text you put here will be visible
    in BlueSky as the description of your plugin. """

import numpy as np
from math import sqrt

# Import the global bluesky objects. Uncomment the ones you need
from bluesky import stack, traf  #, settings, navdb, sim, scr, tools
from bluesky import navdb
from bluesky.tools.aero import ft
from bluesky.tools import geo, areafilter

FT_NM_FACTOR = 0.000164578834   # ft * factor converts to nm
M_FT_FACTOR = 3.280839895       # m * factor converts to feet
SEP_REP_HOR = 3.5               # 3nm is min sep
SEP_REP_VER = 1250              # 1000ft is min sep

POSSIBLE_ACTIONS = {'LEFT', 'RIGHT', 'DIR', 'LNAV'}

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


def direct_distance(hor: float, ver: int) -> float:
    """
    Using the Pythagorean Theorem, the straight-line distance is computed based on the horizontal and vertical distance.

    :param hor: horizontal distance [nm]
    :param ver: vertical distance [ft]
    :return: distance [nm]
    """

    return sqrt(hor ** 2 + ft_to_nm(ver) ** 2)


def give_reward():
    # TODO: determine reward (-1 for collision, [0-1] for avoid + time
    pass


def get_allowed_moves(traf, acid: str) -> set(str):
    # TODO: fix constraints for certain moves (e.g. what waypoint can be used for direct)
    pass


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
    # state = lat, long, alt, tas, rte
    # actionset = HDG +/-, DIR, LNAV
    # transition probability = incresed in higher risk situations
    # reward = based on minimized additional time

    # DONE: determine possible conflicts --> add to set of pairs, ordered by proximity within pairs
    # TODO: get set of allowed actions
    # TODO: determine best action
    # TODO: eval ac of previous instructions (desire to go back to VNAV)
    # TODO: reward function

    positions = {}

    # gather aircraft positions
    for acid, lat, lon, alt_m in zip(traf.id, traf.lat, traf.lon, traf.alt):
        alt = m_to_ft(alt_m)
        positions[acid] = (lat, lon, alt)

    if not positions:
        return

    collision_pairs = get_conflict_pairs(positions)     # list of tuples
    print(collision_pairs)


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
