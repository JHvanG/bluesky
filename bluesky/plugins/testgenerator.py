""" BlueSky plugin template. The text you put here will be visible
    in BlueSky as the description of your plugin. """
import os
import json
import random
import numpy as np
# Import the global bluesky objects. Uncomment the ones you need
from bluesky import stack  #, settings, navdb, traf, sim, scr, tools
from bluesky import navdb
from bluesky.tools.aero import ft
from bluesky.tools import geo, areafilter


ROUTES = "routes/"
DEFINITION = "route_definition.json"
ACID = 0


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
        'update_interval': 20.0,

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
        'APCSPAWN': [
            # A short usage string. This will be printed if you type HELP <name> in the BlueSky console
            'APCSPAWN argument',

            # A list of the argument types your function accepts. For a description of this, see ...
            'txt',

            # The name of your function in this plugin
            apc_spawn(),

            # a longer help text of your function.
            'Spawn aircraft following standard approaches.']
    }

    # init_plugin() should always return these two dicts.
    return config, stackfunctions


### Periodic update functions that are called by the simulation. You can replace
### this by anything, so long as you communicate this in init_plugin

def select_approach() -> (str, str):
    """
    This function selects a random arrival and transition procedure from the definition json.

    :return: strings of the approach transition and standard arrival files
    """

    workdir = os.getcwd()
    file = os.path.join(os.path.join(workdir, ROUTES), DEFINITION)
    with open(file, 'r') as f:
        data = json.load(f)

    rwy = random.choice(list(data.keys()))
    transition = random.choice(list(data[rwy].keys()))
    arrival = random.choice(data[rwy][transition])

    rwy_transition = rwy + "-" + transition
    standard_arrival = transition + "-" + arrival

    return rwy_transition, standard_arrival


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

    flightplan = flightplan | read_fpl_from_txt_file(star)
    flightplan = flightplan | read_fpl_from_txt_file(rwy_transition)

    return flightplan


def spawn_aircraft(flightpath: dict[str: int]):
    """
    This function spawns the aircraft based on the provided flightpath.

    :param flightpath: dictionary containing all waypoints and corresponding altitude constraints
    """
    global ACID

    first = True
    for wpt, alt in flightpath.items():
        if first:
            stack.stack("CRE KL{}, A320, {}, 0, {}, 220".format(ACID, wpt, alt))
            first = False
        else:
            if not alt:
                stack.stack("ADDWPT KL{} {}".format(ACID, wpt))
            else:
                stack.stack("ADDWPT KL{} {} {}".format(ACID, wpt, alt))

    stack.stack("VNAV KL{} ON".format(ACID))

    ACID += 1

    return


def update():
    # TODO: find possible starting points
    # TODO: randomly select approach
    # TODO: fix interval

    trans, star = select_approach()
    print(trans, star)
    flightpath = read_approach_procedure(trans, star)
    # print(flightpath)
    spawn_aircraft(flightpath)
    return


def reset():
    # TODO: reset acid counter
    pass


### Other functions of your plugin
def apc_spawn():
    pass
