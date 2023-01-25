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
SEP_REP_VER = 1500              # 1000ft is min sep
SEP_MIN_HOR = 3.0
SEP_MIN_VER = 1000

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


def is_within_alert_distance(positions, ac1: str, ac2: str) -> bool:
    """
    This function returns a boolean indicating whether two aircraft are within the notification area.

    :param positions: Traffic object containing all info on the present traffic
    :param ac1: id of aircraft 1
    :param ac2: id of aircraft 2
    :return: boolean for a loss of separation
    """
    lat1 = positions[ac1].lat
    lat2 = positions[ac2].lat
    lon1 = positions[ac1].lon
    lon2 = positions[ac2].lon
    alt1 = positions[ac1].alt
    alt2 = positions[ac2].alt

    return within_stated_area(lat1, lat2, lon1, lon2, alt1, alt2, SEP_REP_HOR, SEP_REP_VER)


def is_loss_of_separation(positions, ac1: str, ac2: str) -> bool:
    """
    This function returns a boolean indicating whether a loss of separation has occured.

    :param positions: Traffic object containing all info on the present traffic
    :param ac1: id of aircraft 1
    :param ac2: id of aircraft 2
    :return: boolean for a loss of separation
    """
    lat1 = positions[ac1].lat
    lat2 = positions[ac2].lat
    lon1 = positions[ac1].lon
    lon2 = positions[ac2].lon
    alt1 = positions[ac1].alt
    alt2 = positions[ac2].alt

    return within_stated_area(lat1, lat2, lon1, lon2, alt1, alt2, SEP_MIN_HOR, SEP_MIN_VER)


def has_reached_goal(positions, destinations, ac: str) -> bool:
    """
    This function determines when an aircraft has reached its goal position (the last waypoint in its route).

    :param positions: list of positions and altitudes of all aircraft in the sim
    :param destinations: list of destinations of the aircraft in the sim
    :param ac: aircraft in question
    :return: boolean of reached goal status
    """
    destination = destinations[ac]
    lat, lon, _ = positions[ac]
    # destination = "EH007"
    wplat = navdb.wplat[navdb.wpid.index(destination)]
    wplon = navdb.wplon[navdb.wpid.index(destination)]

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


def get_reward(positions, destinations, ac1: str, ac2: str) -> int:
    # TODO: make more complex
    if is_loss_of_separation(positions, ac1, ac2):
        return -1
    elif has_reached_goal(positions, destinations, ac1) or has_reached_goal(positions, destinations, ac2):
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
    destinations = traf.ap.dest
    # gather aircraft positions
    for acid, lat, lon, alt_m in zip(traf.id, traf.lat, traf.lon, traf.alt):
        alt = m_to_ft(alt_m)
        positions[acid] = (lat, lon, alt)

    if not positions:
        return

    collision_pairs = get_conflict_pairs(positions)     # list of tuples
    print(collision_pairs)
    print(destinations)

    has_reached_goal(None, None, None)


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
