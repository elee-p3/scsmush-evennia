"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""
from evennia import DefaultCharacter
from objects import SCSCharacter


class Character(SCSCharacter):
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
        self.db.origin = "Unknown"
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
        self.db.pose_time = 0.0
        self.db.obs_mode = False

    def get_abilities(self):
        return {"name":self.key, "sex":self.db.sex, "race":self.db.race, "occupation":self.db.occupation,
                "group":self.db.group, "domain":self.db.domain, "element":self.db.element, "origin":self.db.origin,
                "quote":self.db.quote, "profile":self.db.profile, "lf":self.db.lf, "maxlf":self.db.maxlf,
                "ap":self.db.ap, "maxap":self.db.maxap, "ex":self.db.ex, "maxex":self.db.maxex, "power":self.db.power,
                "knowledge":self.db.knowledge, "parry":self.db.parry, "barrier":self.db.barrier, "speed":self.db.speed}

    def get_pose_time(self):
        return self.db.pose_time

    def set_pose_time(self, time):
        self.db.pose_time = time

    def get_obs_mode(self):
        return self.db.obs_mode

    def set_obs_mode(self, mode_flag):
        self.db.obs_mode = mode_flag

    pass
