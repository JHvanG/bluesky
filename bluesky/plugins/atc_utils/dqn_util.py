import os
import csv
from bluesky import stack, traf
from bluesky.plugins.atc_utils import prox_util as pu
from bluesky.plugins.atc_utils.settings import HDG_CHANGE, SAVE_RESULTS


N_INSTRUCTIONS = 0          # counter for the number of instructions given
N_LoS = 0                   # counter for the number of separation losses
N_LEFT = 0                  # counter for the number of times action LEFT is selected
N_RIGHT = 0                 # counter for the number of times action RIGHT is selected
N_DIR = 0                   # counter for the number of times action DIR is selected
N_LNAV = 0                  # counter for the number of times action LNAV is selected

INSTRUCTED_AIRCRAFT = []    # list of aircraft that deviated from their flightpath

ROUTES = {"A": 1, "R": 2, "S": 3}


def reset_variables():
    global N_INSTRUCTIONS
    global N_LoS
    global N_LEFT
    global N_RIGHT
    global N_DIR
    global N_LNAV
    global INSTRUCTED_AIRCRAFT

    N_INSTRUCTIONS = 0
    N_LoS = 0
    N_LEFT = 0
    N_RIGHT = 0
    N_DIR = 0
    N_LNAV = 0
    INSTRUCTED_AIRCRAFT = []

    return


def get_reward(ac1: str, ac2: str) -> (bool, float):
    """
    This function returns the reward obtained from the action that was taken.

    :param ac1: first aircraft in the conflict
    :param ac2: second aircraft in the conflict
    :return: boolean indicating whether separation was lost and reward
    """

    global N_LoS
    global N_INSTRUCTIONS

    N_INSTRUCTIONS += 1

    if pu.is_loss_of_separation(ac1, ac2):
        N_LoS += 1
        return True, -5
    elif not pu.is_within_alert_distance(ac1, ac2):
        return False, 5
    else:
        dist_ac = pu.get_distance_to_ac(ac1, ac2)
        dist_alert = pu.get_distance_to_alert_border()
        return False, min(1, dist_ac / dist_alert)


def engage_lnav(ac: str):
    stack.stack(f"LNAV {ac} ON")
    stack.stack(f"VNAV {ac} ON")
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

    # if this aircraft has not received an instruction yet, add it to the instructed aircraft list
    if ac not in INSTRUCTED_AIRCRAFT:
        INSTRUCTED_AIRCRAFT.append(ac)

    return


def handle_instruction(ac: str, action: str):
    """
    This function checks what instruction was given and calls the appropriate functions to handle these instructions.

    :param ac: aircraft id of aircraft that was given an instruction
    :param action: action that needs to be taken
    """

    global N_LEFT
    global N_RIGHT
    global N_DIR
    global N_LNAV

    if action == "HDG_L":
        N_LEFT += 1
        change_heading(ac, False)
    elif action == "HDG_R":
        N_RIGHT += 1
        change_heading(ac, True)
    elif action == "LNAV":
        N_LNAV += 1
        engage_lnav(ac)


def allow_resume_navigation(conflict_pairs):
    """
    This function checks whether aircraft that received a heading change are allowed to resume their own navigation.
    """

    global INSTRUCTED_AIRCRAFT

    aircraft_to_keep = []

    for ac in INSTRUCTED_AIRCRAFT:
        if not [pair for pair in conflict_pairs if ac in pair[0]] and ac in traf.id:
            engage_lnav(ac)
        else:
            aircraft_to_keep.append(ac)

    INSTRUCTED_AIRCRAFT = aircraft_to_keep

    return


def load_state_data(ac: str) -> (float, float, int, int, int):
    """
    This function gathers all data from one single aircraft that are required for a state definition.

    :param ac: string containing aircraft id
    :return: tuple of all data for one aircraft's state
    """
    idx = traf.id.index(ac)
    lat = traf.lat[idx]
    lon = traf.lon[idx]
    alt = traf.alt[idx]
    hdg = traf.hdg[idx]

    # the route of an aircraft is defined by the last letter in its id
    rte = ROUTES[ac[-1]]

    return lat, lon, alt, hdg, rte


def write_episode_info(data: dict, experiment_name):
    """
    This function simply keeps track of what occured during every episode, saving the actions, loss, conflicts and LoS.

    :param data: episode counter, loss, average reward, n_conflicts, elapsed time and epsilon
    :param experiment_name: string of the experiment name
    """

    if not SAVE_RESULTS:
        return

    workdir = os.getcwd()
    path = os.path.join(workdir, "results/training_results/")
    file = path + "training_results_com" + experiment_name + ".csv"

    if not os.path.exists(path):
        os.makedirs(path)

    action_data = {
            "LoS": N_LoS,
            "instructions": N_INSTRUCTIONS,
            "action LEFT": N_LEFT,
            "action RIGHT": N_RIGHT,
            "action DIRECT": N_DIR,
            "action LNAV": N_LNAV
            }

    contents = data | action_data

    file_exists = os.path.isfile(file)

    with open(file, 'a') as f:
        headers = list(contents.keys())
        writer = csv.DictWriter(f, delimiter=',', lineterminator='\n', fieldnames=headers)

        if not file_exists:
            writer.writeheader()

        writer.writerow(data)

    return
