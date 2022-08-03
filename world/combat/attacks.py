class Attack:
    # TODO: we don't guarantee attack name uniqueness anywhere. This check shouldn't happen here - it should happen in the future command where you're adding attacks to your character
    def __init__(self, name: str, dmg: int, acc: int, flags="", attack_type=""):
        self.name = name.lower() # make case-insensitive # TODO: maybe keep the case here for pretty printing purposes, but do a lower() on check
        self.dmg = dmg
        self.acc = acc
        self.flags = flags
        self.attack_type = attack_type

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name == other
        elif isinstance(other, Attack):
            return self.name == other.name