class Plain :
    def __init__(self, steps = 2, fuel = 1):
        self.steps = steps
        self.fuel = fuel


class Mountain :
    def __init__(self, steps = 3, fuel = 2):
        self.steps = steps
        self.fuel = fuel


class Road :
    def __init__(self, steps, fuel = 2):
        self.steps = steps
        self.fuel = fuel


class Pond :
    def __init__(self, steps = None , fuel = None):
        self.steps = steps
        self.fuel = fuel
