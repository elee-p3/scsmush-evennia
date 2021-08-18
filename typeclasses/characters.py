"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""
from evennia import DefaultCharacter


class Character(DefaultCharacter):
    """
    The Character defaults to reimplementing some of base Object's hook methods with the
    following functionality:

    at_basetype_setup - always assigns the DefaultCmdSet to this object type
                    (important!)sets locks so character cannot be picked up
                    and its commands only be called by itself, not anyone else.
                    (to change things, use at_object_creation() instead).
    at_after_move(source_location) - Launches the "look" command after every move.
    at_post_unpuppet(account) -  when Account disconnects from the Character, we
                    store the current location in the pre_logout_location Attribute and
                    move it to a None-location so the "unpuppeted" character
                    object does not need to stay on grid. Echoes "Account has disconnected"
                    to the room.
    at_pre_puppet - Just before Account re-connects, retrieves the character's
                    pre_logout_location Attribute and move it back on the grid.
    at_post_puppet - Echoes "AccountName has entered the game" to the room.

    """

    def at_object_creation(self):
        "This is called when object is first created, only."
        self.db.sex = "Unknown"
        self.db.race = "Unknown"
        self.db.occupation = "Unknown"
        self.db.group = "Unknown"
        self.db.domain = "Unknown"
        self.db.element = "Unknown"
        self.db.quote = '"..."'
        self.db.profile = "This character is shrouded in mystery."
        self.db.lf = 1000
        self.db.maxlf = 1000
        self.db.ap = 100
        self.db.maxap = 100
        self.db.ex = 0
        self.db.maxex = 100
        self.db.power = 100
        self.db.knowledge = 100
        self.db.parry = 100
        self.db.barrier = 100
        self.db.speed = 100

    def get_abilities(self):
        return self.db.sex, self.db.race, self.db.occupation, self.db.group, self.db.domain, self.db.element, \
               self.db.quote, self.db.profile, self.db.lf, self.db.maxlf, self.db.ap, self.db.maxap, self.db.ex, self.db.maxex, self.db.power, self.db.knowledge, self.db.parry, self.db.barrier, self.db.speed

    pass
