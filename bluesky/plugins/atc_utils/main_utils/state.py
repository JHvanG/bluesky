class State(object):
    def __init__(self, lat1: float, lon1: float, alt1: int, hdg1: int, rte1: int, lat2: float, lon2: float, alt2: int,
                 hdg2: int, rte2: int, com_lat: float, com_lon: float, com_hdg: float):
        self.lat1 = lat1
        self.lon1 = lon1
        self.alt1 = alt1
        self.hdg1 = hdg1
        self.rte1 = rte1
        self.lat2 = lat2
        self.lon2 = lon2
        self.alt2 = alt2
        self.hdg2 = hdg2
        self.rte2 = rte2
        self.com_lat = com_lat
        self.com_lon = com_lon
        self.com_hdg = com_hdg

    def get_route(self, ac: int):
        if ac == 1:
            return self.rte1
        elif ac == 2:
            return self.rte2

    def get_state_as_list(self) -> list:
        """
        Convert the state to a list format in order for the model to be able to use it.

        :return: List representation of the state
        """
        state_list = [self.lat1, self.lon1, self.alt1, self.hdg1, self.rte1,
                      self.lat2, self.lon2, self.alt2, self.hdg2, self.rte2,
                      self.com_lat, self.com_lon, self.com_hdg]
        return state_list
