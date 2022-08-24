class Attack:
    # TODO: we don't guarantee attack name uniqueness anywhere. This check shouldn't happen here - it should happen in the future command where you're adding attacks to your character
    def __init__(self, name: str, dmg: int, acc: int, base_stat="", flags=""):
        self.name = name # make case-insensitive
        self.dmg = dmg
        self.acc = acc
        self.base_stat = base_stat
        self.flags = flags

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name.lower() == other.lower()
        elif isinstance(other, Attack):
            return self.name.lower() == other.name.lower()