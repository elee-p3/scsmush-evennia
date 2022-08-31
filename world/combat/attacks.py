class Attack:
    # TODO: we don't guarantee attack name uniqueness anywhere. This check shouldn't happen here - it should happen in the future command where you're adding attacks to your character
    def __init__(self, name: str, ap_change: int, dmg: int, acc: int, base_stat="", effects=""):
        self.name = name # make case-insensitive
        self.ap_change = ap_change
        self.dmg = dmg
        self.acc = acc
        self.base_stat = base_stat
        self.effects = effects

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name.lower() == other.lower()
        elif isinstance(other, Attack):
            return self.name.lower() == other.name.lower()