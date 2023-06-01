""" BlueSky plugin template. The text you put here will be visible
    in BlueSky as the description of your plugin. """
import os
import json
import numpy as np
# Import the global bluesky objects. Uncomment the ones you need
from bluesky import stack  #, settings, navdb, traf, sim, scr, tools
from bluesky import navdb
from bluesky.tools.aero import ft
from bluesky.tools import geo, areafilter


ROUTES = "routes/"
DEFINITION = "route_definition.json"
ELEMENT_COUNTER = 0


### Initialization function of your plugin. Do not change the name of this
### function, as it is the way BlueSky recognises this file as a plugin.
def init_plugin():

    # Addtional initilisation code

    # Configuration parameters
    config = {
        # The name of your plugin
        'plugin_name':     'APPROACHES',

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
        'DRAW': [
            # A short usage string. This will be printed if you type HELP <name> in the BlueSky console
            'DRAW useless necessity',

            # A list of the argument types your function accepts. For a description of this, see ...
            'txt',

            # The name of your function in this plugin
            draw_approaches,

            # a longer help text of your function.
            'Draw all available approaches.']
    }

    # init_plugin() should always return these two dicts.
    return config, stackfunctions


### Periodic update functions that are called by the simulation. You can replace
### this by anything, so long as you communicate this in init_plugin

def update():
    pass


def reset():
    global ELEMENT_COUNTER
    ELEMENT_COUNTER = 0
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


### Other functions of your plugin
def draw_approaches(x=0):
    """
    This function draws the approaches on the screen.
    """
    approaches = load_all_approaches()

    for transition in list(approaches.keys()):
        transition_plan = read_fpl_from_txt_file(transition)
        first_wpt = {list(transition_plan.keys())[0]: list(transition_plan.values())[0]}
        first = True
        print(transition_plan)
        for star in approaches[transition]:
            if first:
                flightplan = read_fpl_from_txt_file(star) | transition_plan
                first = False
            else:
                flightplan = read_fpl_from_txt_file(star) | first_wpt

            for prev, cur in zip(list(flightplan.keys()), list(flightplan.keys())[1:]):
                global ELEMENT_COUNTER
                stack.stack("LINE {} {} {}".format(ELEMENT_COUNTER, prev, cur))
                if prev in list(transition_plan.keys()) and cur in list(transition_plan.keys()):
                    print("damn right")
                    stack.stack("COLOUR {} RED".format(ELEMENT_COUNTER))
                ELEMENT_COUNTER += 1

    return

