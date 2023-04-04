""" BlueSky plugin template. The text you put here will be visible
    in BlueSky as the description of your plugin. """
import os
import json
import random
import numpy as np
# Import the global bluesky objects. Uncomment the ones you need
from bluesky import stack, traf  #, settings, navdb, sim, scr, tools
from bluesky import navdb
from bluesky.tools.aero import ft
from bluesky.tools import geo, areafilter


ROUTES = "routes/"
# DEFINITION = "route_definition.json"
# DEFINITION = "route_definition_south_west.json"
DEFINITION = "route_definition_equal.json"
ACID = 0
MAX_AC = 20
ELEMENT_COUNTER = 0
PREVIOUS_ARRIVAL = None
ONLY_TRANSITION = True


### Initialization function of your plugin. Do not change the name of this
### function, as it is the way BlueSky recognises this file as a plugin.
def init_plugin():

    # Addtional initilisation code

    # Configuration parameters
    config = {
        # The name of your plugin
        'plugin_name':     'APCSPAWN',

        # The type of this plugin. For now, only simulation plugins are possible.
        'plugin_type':     'sim',

        # Update interval in seconds. By default, your plugin's update function(s)
        # are called every timestep of the simulation. If your plugin needs less
        # frequent updates provide an update interval.
        'update_interval': 200.0,

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
        'DRAW': [
            # A short usage string. This will be printed if you type HELP <name> in the BlueSky console
            'APCSPAWN argument',

            # A list of the argument types your function accepts. For a description of this, see ...
            'txt',

            # The name of your function in this plugin
            draw,

            # a longer help text of your function.
            'Spawn aircraft following standard approaches.']
    }

    # init_plugin() should always return these two dicts.
    return config, stackfunctions


### Periodic update functions that are called by the simulation. You can replace
### this by anything, so long as you communicate this in init_plugin

def select_approach() -> (str, str, str):
    """
    This function selects a random arrival and transition procedure from the definition json.

    :return: strings of the approach transition and standard arrival files
    """

    global PREVIOUS_ARRIVAL

    workdir = os.getcwd()
    file = os.path.join(os.path.join(workdir, ROUTES), DEFINITION)
    with open(file, 'r') as f:
        data = json.load(f)

    rwy = random.choice(list(data.keys()))
    route_addition = ""

    if ONLY_TRANSITION:
        all_transitions = list(data[rwy].keys())
        transition = random.choice([tran for tran in all_transitions if tran != PREVIOUS_ARRIVAL])
        arrival = random.choice(data[rwy][transition])
        PREVIOUS_ARRIVAL = transition
        route_addition = transition[0]
        # print("spawning ac at {}".format(transition))
    else:
        transition = random.choice(list(data[rwy].keys()))
        all_arrivals = data[rwy][transition]
        arrival = random.choice([arr for arr in all_arrivals if arr != PREVIOUS_ARRIVAL])
        PREVIOUS_ARRIVAL = arrival
        # print("spawning ac at {}".format(arrival))

    rwy_transition = rwy + "-" + transition
    standard_arrival = transition + "-" + arrival

    return rwy_transition, standard_arrival, route_addition


def read_fpl_from_txt_file(filename: str) -> dict[str: int]:
    """
    Utility function to read a flightplan from a txt file.

    :param filename: name of the file to be opened
    :return: dictionary containing the waypoints and possible altitude constraints
    """
    flightplan = {}

    workdir = os.getcwd()
    path = os.path.join(workdir, ROUTES)
    file = path + "{}.txt".format(filename)

    with open(file, 'r') as f:
        for line in f:
            line = line.strip()

            if "@" in line:
                line = line.split("@")
                wpt = line[0]
                alt = line[1]
                if "FL" in alt:
                    alt = alt.replace("FL", "")
                    alt = int(alt) * 100
                else:
                    alt = int(alt)
            else:
                wpt = line
                alt = None

            flightplan[wpt] = alt

    return flightplan


def read_approach_procedure(rwy_transition: str, star: str) -> dict:
    """
    This function reads a file containing an approach procedure defined by waypoints and altitude constraints.

    :param rwy_transition: string containing the name of the transition procedure
    :param star: string containing the name of the standard arrival procedure
    :return: dictionary containing all waypoints and a possible altitude constraint
    """
    flightplan = {}

    if ONLY_TRANSITION:
        flightplan = flightplan | read_fpl_from_txt_file(rwy_transition)
    else:
        flightplan = flightplan | read_fpl_from_txt_file(star)
        flightplan = flightplan | read_fpl_from_txt_file(rwy_transition)

    return flightplan


def spawn_aircraft(flightpath: dict[str: int], route_addition: str):
    """
    This function spawns the aircraft based on the provided flightpath.

    :param flightpath: dictionary containing all waypoints and corresponding altitude constraints
    """
    global ACID

    # determine heading
    wp1 = list(flightpath.keys())[0]
    wp2 = list(flightpath.keys())[1]

    idx1 = navdb.getwpidx(wp1)
    idx2 = navdb.getwpidx(wp2)

    lat1 = navdb.wplat[idx1]
    lon1 = navdb.wplon[idx1]
    lat2 = navdb.wplat[idx2]
    lon2 = navdb.wplon[idx2]

    hdg, _ = geo.qdrdist(lat1, lon1, lat2, lon2)

    first = True
    for wpt, alt in flightpath.items():
        if first:
            stack.stack("CRE AC{}_{}, A320, {}, {}, {}, 220".format(ACID, route_addition, wpt, hdg, alt))
            first = False
        else:
            if not alt:
                stack.stack("ADDWPT AC{}_{} {}".format(ACID, route_addition, wpt))
            else:
                stack.stack("ADDWPT AC{}_{} {} {}".format(ACID, route_addition, wpt, alt))

    stack.stack("VNAV AC{}_{} ON".format(ACID, route_addition))

    ACID += 1

    return


def update():
    n_ac = len(traf.id)

    # uncomment for test prints
    # if ACID > 0:
    #     idx = traf.id.index("AC{}_{}".format(ACID - 1))
    #     print("AC{}_{} loaded flightplan: {}".format(ACID - 1, traf.ap.route[idx].wpname))

    # uncomment for old spawining after one another
    # if n_ac < MAX_AC:
    #
    #     trans, star = select_approach()
    #     # print(trans, star)
    #     flightpath = read_approach_procedure(trans, star)
    #     spawn_aircraft(flightpath)

    # spawning at the same time
    if n_ac < MAX_AC - 1:
        trans1, star1, add1 = select_approach()
        trans2, star2, add2 = select_approach()

        flightpath1 = read_approach_procedure(trans1, star1)
        flightpath2 = read_approach_procedure(trans2, star2)

        spawn_aircraft(flightpath1, add1)
        spawn_aircraft(flightpath2, add2)

    return


def reset():
    print("resetting spawn plugin")
    global ACID
    global PREVIOUS_ARRIVAL
    global ELEMENT_COUNTER

    ELEMENT_COUNTER = 0
    ACID = 0
    PREVIOUS_ARRIVAL = None

    return


def load_all_approaches() -> dict[str: list[str]]:
    """
    This function loads all approaches that can be flown in the simulator.

    :return: dictionary of stars, for each transition
    """
    approaches = {}

    workdir = os.getcwd()
    file = os.path.join(os.path.join(workdir, ROUTES), DEFINITION)

    with open(file, 'r') as f:
        data = json.load(f)

        for rwy in list(data.keys()):
            for transition in list(data[rwy].keys()):
                arrivals = []
                for arrival in data[rwy][transition]:
                    arrivals.append(transition + "-" + arrival)
                approaches[rwy + "-" + transition] = arrivals

    return approaches


### Other functions of your plugin
def draw(x=0):
    """
        This function draws the approaches on the screen.
        """
    approaches = load_all_approaches()

    for transition in list(approaches.keys()):
        transition_plan = read_fpl_from_txt_file(transition)
        # first_wpt = {list(transition_plan.keys())[0]: list(transition_plan.values())[0]}
        # first = True

        for prev, cur in zip(list(transition_plan.keys()), list(transition_plan.keys())[1:]):
            global ELEMENT_COUNTER
            stack.stack("LINE {} {} {}".format(ELEMENT_COUNTER, prev, cur))
            ELEMENT_COUNTER += 1

        # for star in approaches[transition]:
        #     if first:
        #         flightplan = read_fpl_from_txt_file(star) | transition_plan
        #         first = False
        #     else:
        #         flightplan = read_fpl_from_txt_file(star) | first_wpt
        #
        #     for prev, cur in zip(list(flightplan.keys()), list(flightplan.keys())[1:]):
        #         global ELEMENT_COUNTER
        #         stack.stack("LINE {} {} {}".format(ELEMENT_COUNTER, prev, cur))
        #         ELEMENT_COUNTER += 1

    return
