""" BlueSky plugin template. The text you put here will be visible
    in BlueSky as the description of your plugin. """
import numpy as np
# Import the global bluesky objects. Uncomment the ones you need
from bluesky import stack, traf  #, settings, navdb, traf, sim, scr, tools
from bluesky import navdb
from bluesky.tools.aero import ft
from bluesky.tools import geo, areafilter

from bluesky.plugins.atc_utils import prox_util as pu
from cpa.closest_point_of_approach import closest_point_of_approach

### Initialization function of your plugin. Do not change the name of this
### function, as it is the way BlueSky recognises this file as a plugin.
def init_plugin():

    # Addtional initilisation code

    # Configuration parameters
    config = {
        # The name of your plugin
        'plugin_name':     'PLAYGROUND',

        # The type of this plugin. For now, only simulation plugins are possible.
        'plugin_type':     'sim',

        # Update interval in seconds. By default, your plugin's update function(s)
        # are called every timestep of the simulation. If your plugin needs less
        # frequent updates provide an update interval.
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
        'PLAYGROUND': [
            # A short usage string. This will be printed if you type HELP <name> in the BlueSky console
            'PLAYGROUND Airport/runway',

            # A list of the argument types your function accepts. For a description of this, see ...
            'txt',

            # The name of your function in this plugin
            go,

            # a longer help text of your function.
            'Playground for testing random stuff.']
    }

    stack.stack("CRE AC1, A320, EHAM, 45, 5000, 220")
    stack.stack("CRE AC2, A320, EHLE, 290, 5000, 220")

    # init_plugin() should always return these two dicts.
    return config, stackfunctions


### Periodic update functions that are called by the simulation. You can replace
### this by anything, so long as you communicate this in init_plugin

def update():
    idx1 = traf.id.index("AC1")
    idx2 = traf.id.index("AC2")

    ac1 = (traf.lat[idx1], traf.lon[idx1], traf.gsnorth[idx1], traf.gseast[idx1])
    ac2 = (traf.lat[idx2], traf.lon[idx2], traf.gsnorth[idx2], traf.gseast[idx2])

    print("Closest distance: {} nm".format(closest_point_of_approach(ac1, ac2)))

def reset():
    pass

### Other functions of your plugin
def go(rwyname):
    pass
