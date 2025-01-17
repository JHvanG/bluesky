"""
This file contains all functions used for anything regarding aircraft proximity.
"""

from math import sqrt
from bluesky import traf
from bluesky.tools import geo


FT_NM_FACTOR = 0.000164578834   # ft * factor converts to nm
M_FT_FACTOR = 3.280839895       # m * factor converts to feet

SEP_REP_HOR = 3.5               # report within 3.5 nm
SEP_REP_VER = 1500              # report within 1500 ft
SEP_MIN_HOR = 3.0               # 3 nm is min sep
SEP_MIN_VER = 1000              # 1000 ft is min sep


def m_to_ft(alt: int) -> int:
    return int(alt * M_FT_FACTOR)


def ft_to_nm(alt: int) -> float:
    return alt * FT_NM_FACTOR


def get_lat(ac):
    idx = traf.id.index(ac)
    return traf.lat[idx]


def get_lon(ac):
    idx = traf.id.index(ac)
    return traf.lon[idx]


def get_alt(ac):
    idx = traf.id.index(ac)
    return m_to_ft(traf.alt[idx])


def both_aircraft_exits(ac1: str, ac2: str) -> bool:
    """
    Simple function that returns true only if both aircraft are present in the simulation.

    :param ac1: string of id of ac1
    :param ac2: string of id of ac2
    :return: bool indicating whether both exits
    """
    if ac1 in traf.id and ac2 in traf.id:
        return True
    else:
        print("one or both aircraft despawned!")
        return False


def within_stated_area(lat1: float, lat2: float, lon1: float, lon2: float,
                       alt1: int, alt2: int, h_lim: float, v_lim: int) -> bool:
    """
    This function returns true when two aircraft are within the stated area.

    :param lat1: ac1 latitude
    :param lat2: ac2 latitude
    :param lon1: ac1 longitude
    :param lon2: ac2 longitude
    :param alt1: ac1 altitude (ft)
    :param alt2: ac2 altitude (ft)
    :param h_lim: horizontal limit (nm)
    :param v_lim: vertical limit (ft)
    :return: boolean of within limits
    """
    _, dist_h = geo.qdrdist(lat1, lon1, lat2, lon2)  # bearing, distance (nm)
    dist_v = abs(alt1 - alt2)  # distance (ft)

    if dist_h <= h_lim and dist_v <= v_lim:
        return True
    else:
        return False


def is_within_alert_distance(ac1: str, ac2: str) -> bool:
    """
    This function returns a boolean indicating whether two aircraft are within the notification area.

    :param ac1: id of aircraft 1
    :param ac2: id of aircraft 2
    :return: boolean for a loss of separation
    """
    if not both_aircraft_exits(ac1, ac2):
        return False

    lat1 = get_lat(ac1)
    lat2 = get_lat(ac2)
    lon1 = get_lon(ac1)
    lon2 = get_lon(ac2)
    alt1 = get_alt(ac1)  # ft
    alt2 = get_alt(ac2)  # ft

    return within_stated_area(lat1, lat2, lon1, lon2, alt1, alt2, SEP_REP_HOR, SEP_REP_VER)


def is_loss_of_separation(ac1: str, ac2: str) -> bool:
    """
    This function returns a boolean indicating whether a loss of separation has occurred.

    :param ac1: id of aircraft 1
    :param ac2: id of aircraft 2
    :return: boolean for a loss of separation
    """
    if not both_aircraft_exits(ac1, ac2):
        return False

    lat1 = get_lat(ac1)
    lat2 = get_lat(ac2)
    lon1 = get_lon(ac1)
    lon2 = get_lon(ac2)
    alt1 = get_alt(ac1)  # ft
    alt2 = get_alt(ac2)  # ft

    return within_stated_area(lat1, lat2, lon1, lon2, alt1, alt2, SEP_MIN_HOR, SEP_MIN_VER)


def direct_distance(hor: float, ver: int) -> float:
    """
    Using the Pythagorean Theorem, the straight-line distance is computed based on the horizontal and vertical distance.

    :param hor: horizontal distance [nm]
    :param ver: vertical distance [ft]
    :return: distance [nm]
    """

    return sqrt(hor ** 2 + ft_to_nm(ver) ** 2)


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
        lat_a, lon_a, alt_a = position_list[a]  # alt in ft
        lat_b, lon_b, alt_b = position_list[b]  # alt in ft

        _, dist_h = geo.qdrdist(lat_a, lon_a, lat_b, lon_b)   # bearing, distance (nm)
        dist_v = abs(alt_a - alt_b)

        # distance checks out, bearing is weird
        # print(f"Distance between {a} and {b} is {dist_h}nm horizontally and {dist_v}ft vertically.")

        if dist_h < SEP_REP_HOR and dist_v < SEP_REP_VER:
            # print(f"{a} and {b} are within the notification range of each other")
            conflict_list.append((str(a), str(b)))
            conflict_dist.append(direct_distance(dist_h, dist_v))

    sorted_conflicts = [x for _, x in sorted(zip(conflict_dist, conflict_list))]

    return sorted_conflicts
