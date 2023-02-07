class State(object):
    def __init__(self, lat1: float, lon1: float, alt1: int, tas1: int, cur1: int, nxt1: int,
                 lat2: float, lon2: float, alt2: int, tas2: int, cur2: int, nxt2: int):
        self.lat1 = lat1
        self.lon1 = lon1
        self.alt1 = alt1
        self.tas1 = tas1
        self.cur1 = cur1
        self.nxt1 = nxt1
        self.lat2 = lat2
        self.lon2 = lon2
        self.alt2 = alt2
        self.tas2 = tas2
        self.cur2 = cur2
        self.nxt2 = nxt2

    def get_next_waypoint(self, ac: int):
        if ac == 1:
            return self.nxt1
        elif ac == 2:
            return self.nxt2

    def get_state_as_list(self) -> list:
        """
        Convert the state to a list format in order for the model to be able to use it.

        :return: List representation of the state
        """
        state_list = [self.lat1, self.lon1, self.alt1, self.tas1, self.cur1, self.nxt1,
                      self.lat2, self.lon2, self.alt2, self.tas2, self.cur2, self.nxt2]
        return state_list
