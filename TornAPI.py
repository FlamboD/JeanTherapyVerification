class TornAPI:
    _BASE = "https://api.torn.com"

    def __init__(self, key):
        self.selections = None
        self.endpoint = None
        self.key = key

    def torn(self, *, competition: bool = False):
        self.endpoint = "torn"
        self.selections = []
        if competition: self.selections.append("competition")
        return self._build()

    def user(self, user_id, *, basic: bool = False, profile: bool = False):
        self.endpoint = f"user/{user_id}"
        self.selections = []
        if basic: self.selections.append("basic")
        if profile: self.selections.append("profile")
        return self._build()

    def _build(self):
        return f"{TornAPI._BASE}/{self.endpoint}/?selections={','.join(self.selections)}&key={self.key}"