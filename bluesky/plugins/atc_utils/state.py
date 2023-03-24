class State(object):
    def __init__(self, bearing: float, dist: float, alt1: int, hdg1: int, rte1: int, alt2: int,
                 hdg2: int, rte2: int, com_bearing: float, com_dist: float, com_hdg: float):
        self.bearing = bearing
        self.dist = dist
        self.alt1 = alt1
        self.hdg1 = hdg1
        self.rte1 = rte1
        self.alt2 = alt2
        self.hdg2 = hdg2
        self.rte2 = rte2
        self.com_bearing = com_bearing
        self.com_dist = com_dist
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
        state_list = [self.bearing, self.dist, self.alt1, self.hdg1, self.rte1, self.alt2, self.hdg2, self.rte2,
                      self.com_bearing, self.com_dist, self.com_hdg]
        return state_list
