"""
This file contains all functions used for anything regarding aircraft proximity.
"""

from math import sqrt
from bluesky import traf
from bluesky.tools import geo


FT_NM_FACTOR = 0.000164578834   # ft * factor converts to nm
M_FT_FACTOR = 3.280839895       # m * factor converts to feet
MS_KT_FACTOR = 1.94384449

# TODO: change this
SEP_REP_HOR = 5.0               # report within 5 nm (was 3.5 nm)
SEP_REP_VER = 1500              # report within 1500 ft
SEP_MIN_HOR = 3.0               # 3 nm is min sep
SEP_MIN_VER = 1000              # 1000 ft is min sep


def m_to_ft(alt: int) -> int:
    return int(alt * M_FT_FACTOR)


def ft_to_nm(alt: int) -> float:
    return alt * FT_NM_FACTOR


def ms_to_kt(spd: float) -> float:
    return spd * MS_KT_FACTOR


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


def has_lost_separation(ac: str) -> bool:
    """
    This function checks if the provided aircraft has lost separation with any aircraft.

    :param ac: aircraft id
    :return: boolean indicating whether separation was lost
    """

    for acid in traf.id:
        if not ac == acid and is_loss_of_separation(ac, acid):
            return True

    return False


def direct_distance(hor: float, ver: int) -> float:
    """
    Using the Pythagorean Theorem, the straight-line distance is computed based on the horizontal and vertical distance.

    :param hor: horizontal distance [nm]
    :param ver: vertical distance [ft]
    :return: distance [nm]
    """

    return sqrt(hor ** 2 + ft_to_nm(ver) ** 2)


def get_distance_to_ac(ac1: str, ac2: str):
    """
    Returns the direct distance between the two provided aircraft.

    :param ac1: aircraft id of first aircraft
    :param ac2: aircraft id of second aircraft
    :return: direct distance between the two aircraft
    """

    lat1 = get_lat(ac1)
    lat2 = get_lat(ac2)
    lon1 = get_lon(ac1)
    lon2 = get_lon(ac2)
    alt1 = get_alt(ac1)  # ft
    alt2 = get_alt(ac2)  # ft

    _, dist_h = geo.qdrdist(lat1, lon1, lat2, lon2)  # bearing, distance (nm)
    dist_v = abs(alt1 - alt2)  # altitude difference (ft)

    return direct_distance(dist_h, dist_v)


def get_distance_to_alert_border():
    return direct_distance(SEP_REP_HOR, SEP_REP_VER)


def get_conflict_pairs() -> list[tuple[str, str]]:
    """
    This functions returns a list of pairs that are within alerting distance of each other. If there are more, then the
    closest is selected. Aircraft that have lost separation are excluded.

    :return: list of aircraft ID pairs (strings)
    """

    conflict_list = []

    for ac1 in traf.id:
        current_shortest_dist = None
        current_shortest_pair = None

        for ac2 in traf.id:
            # the ac's cannot be identical, have to be within alerting distance, but not in a loss of separation
            if not ac1 == ac2 and not is_loss_of_separation(ac1, ac2) and is_within_alert_distance(ac1, ac2):
                # the first pair fills in the values initially
                if not current_shortest_dist:
                    current_shortest_dist = get_distance_to_ac(ac1, ac2)
                    current_shortest_pair = (ac1, ac2)
                else:
                    # if the distance between the current pair is shortest, replace the current values
                    dist = get_distance_to_ac(ac1, ac2)
                    if dist < current_shortest_dist:
                        current_shortest_dist = dist
                        current_shortest_pair = (ac1, ac2)

        if current_shortest_pair:
            conflict_list.append(current_shortest_pair)

    return conflict_list


def get_centre_of_mass(ac: str) -> tuple[float, float, int]:
    """
    This function determines the centre of mass of the aircraft surrounding the aircraft in question. For this, the
    alerting distance is used.

    :param ac: id of aircraft for which the scenario is evaluated
    :return: lat, lon and average heading of centre of mass
    """

    lat = 0
    lon = 0
    hdg = 0

    ac_in_proximity = 0

    for acid in traf.id:
        if acid != ac and is_within_alert_distance(ac, acid):
            ac_in_proximity += 1
            idx = traf.id.index(acid)
            lat += traf.lat[idx]
            lon += traf.lon[idx]
            hdg += traf.hdg[idx]

    if not ac_in_proximity == 0:
        lat /= ac_in_proximity
        lon /= ac_in_proximity
        hdg /= ac_in_proximity

    return lat, lon, int(hdg)
