""" BlueSky plugin template. The text you put here will be visible
    in BlueSky as the description of your plugin. """

import numpy as np
from math import sqrt

# Import the global bluesky objects. Uncomment the ones you need
from bluesky import stack, traf  #, settings, navdb, sim, scr, tools
from bluesky import navdb
from bluesky.tools.aero import ft
from bluesky.tools import geo, areafilter


EPISODE_COUNTER = 0
EPISODE_LIMIT = 14400           # 14400 updates equates to approximately 2 hours of simulation time

PREVIOUS_ACTIONS = []           # buffer for previous actions with the given state and the aircraft pair


### Initialization function of your plugin. Do not change the name of this
### function, as it is the way BlueSky recognises this file as a plugin.
def init_plugin():

    # Addtional initilisation code

    # Configuration parameters
    config = {
        # The name of your plugin
        'plugin_name':     'EXPERIMENTAL',

        # The type of this plugin. For now, only simulation plugins are possible.
        'plugin_type':     'sim',

        # Update interval in seconds. By default, your plugin's update function(s)
        # are called every timestep of the simulation. If your plugin needs less
        # frequent updates provide an update interval.
        # Delta T = 0.05s in the simulation
        'update_interval': 10.0,

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
        'EXPERIMENTAL': [
            # A short usage string. This will be printed if you type HELP <name> in the BlueSky console
            'EXPERIMENTAL argument',

            # A list of the argument types your function accepts. For a description of this, see ...
            'txt',

            # The name of your function in this plugin
            experimental,

            # a longer help text of your function.
            'First test plugin to help with plugin development.']
    }

    # init_plugin() should always return these two dicts.
    return config, stackfunctions


def update():
    print(PREVIOUS_ACTIONS)
    PREVIOUS_ACTIONS.append('a')
    reset()
    return


def reset():
    pass

### Other functions of your plugin
def experimental(argument):
    pass
