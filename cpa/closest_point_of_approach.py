import numpy as np
from bluesky.tools.aero import Rearth
from bluesky.tools.geo import qdrdist
from bluesky.plugins.atc_utils import prox_util as pu


# Adapted from the traffic class:
def update_pos(lat, lon, gsnorth, gseast, dt):
    # Update position
    lat = lat + np.degrees(dt * gsnorth / Rearth)
    coslat = np.cos(np.deg2rad(lat))
    lon = lon + np.degrees(dt * gseast / coslat / Rearth)
    return lat, lon


def cpa_for_playground(ac1: tuple[float, float, float, float], ac2: tuple[float, float, float, float]) -> tuple[list, list, list]:
    """
    duplicate function which returns more for drawing.

    :param ac1: lat, lon, gsnorth, gseast       [ddeg, ddeg, m/s, m/s]
    :param ac2: lat, lon, gsnorth, gseast       [ddeg, ddeg, m/s, m/s]
    :return: three lists of points and their distance between
    """

    dt = 10             # seconds
    step = 0            # counts the number of steps taken
    max_steps = 30      # enough for 5 minutes of planning ahead

    lat1, lon1, gsnorth1, gseast1 = ac1
    lat2, lon2, gsnorth2, gseast2 = ac2

    ac1_pts = []
    ac2_pts = []
    dist = []

    _, min_dist = qdrdist(lat1, lon1, lat2, lon2)

    while step <= max_steps:
        step += 1

        lat1, lon1 = update_pos(lat1, lon1, gsnorth1, gseast1, dt)
        lat2, lon2 = update_pos(lat2, lon2, gsnorth2, gseast2, dt)

        ac1_pts.append((lat1, lon1))
        ac2_pts.append((lat2, lon2))

        _, cur_dist = qdrdist(lat1, lon1, lat2, lon2)

        if cur_dist < min_dist:
            min_dist = cur_dist
            dist.append(cur_dist)
        else:
            return ac1_pts, ac2_pts, dist

    return ac1_pts, ac2_pts, dist


def closest_point_of_approach(ac1: tuple[float, float, float, float], ac2: tuple[float, float, float, float]) -> float:
    """
    This function gives a discretized solution to the Closest Point of Approach problem. This indicates the point where
    two craft, adhering to a fixed heading and speed have the least lateral separation. This solution gives the closest
    distance from a discrete set of distances. Computed until distance increases again, which indicates the CPA is
    behind the projected positions

    :param ac1: lat, lon, gsnorth, gseast       [ddeg, ddeg, m/s, m/s]
    :param ac2: lat, lon, gsnorth, gseast       [ddeg, ddeg, m/s, m/s]
    :return: shortest distance                  [nm]
    """

    dt = 10             # seconds
    step = 0            # counts the number of steps taken
    max_steps = 30      # enough for 5 minutes of planning ahead

    lat1, lon1, gsnorth1, gseast1 = ac1
    lat2, lon2, gsnorth2, gseast2 = ac2

    _, min_dist = qdrdist(lat1, lon1, lat2, lon2)

    while step <= max_steps:
        step += 1

        lat1, lon1 = update_pos(lat1, lon1, gsnorth1, gseast1, dt)
        lat2, lon2 = update_pos(lat2, lon2, gsnorth2, gseast2, dt)

        _, cur_dist = qdrdist(lat1, lon1, lat2, lon2)

        if cur_dist < min_dist:
            min_dist = cur_dist
        else:
            if step == 1:
                print("The CPA is behind the aircraft")
                return 1000000.0
            print("Found closest distance")
            return min_dist

    return min_dist