import time
from deriv_api import DerivAPI

class AutoCopy:
    def __init__(self, token, stake=1, duration=5):
        self.api = DerivAPI(token)
        self.stake = stake
        self.duration = duration
