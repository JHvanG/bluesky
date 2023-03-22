""" BlueSky plugin template. The text you put here will be visible
    in BlueSky as the description of your plugin. """
import numpy as np
from bluesky import stack, traf
from bluesky.plugins.atc_utils import prox_util as pu
from itertools import combinations

def init_plugin():

    # Addtional initilisation code

    # Configuration parameters
    config = {
        # The name of your plugin
        'plugin_name':     'HIGHLIGHT',

        # The type of this plugin. For now, only simulation plugins are possible.
        'plugin_type':     'sim',

        # Update interval in seconds. By default, your plugin's update function(s)
        # are called every timestep of the simulation. If your plugin needs less
        # frequent updates provide an update interval.
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
        'HIGHLIGHT': [
            # A short usage string. This will be printed if you type HELP <name> in the BlueSky console
            'HIGHLIGHT Airport/runway',

            # A list of the argument types your function accepts. For a description of this, see ...
            'txt',

            # The name of your function in this plugin
            highlighter,

            # a longer help text of your function.
            'Highlight conflicts.']
    }

    # init_plugin() should always return these two dicts.
    return config, stackfunctions


### Periodic update functions that are called by the simulation. You can replace
### this by anything, so long as you communicate this in init_plugin

def update():
    for ac1, ac2 in list(combinations(traf.id, 2)):
        if pu.is_loss_of_separation(ac1, ac2):
            stack.stack("COLOUR {} RED".format(ac1))
            stack.stack("COLOUR {} RED".format(ac2))
    pass


def reset():
    pass


### Other functions of your plugin
def highlighter(x=0):
    pass
