"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

"""
from evennia import DefaultCharacter
from evennia.utils import logger
from django.utils.translation import gettext as _

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

    def move_to(
            self,
            destination,
            quiet=False,
            emit_to_obj=None,
            use_destination=True,
            to_none=False,
            move_hooks=True,
            **kwargs,
    ):
        """
        Moves this object to a new location.

        Args:
            destination (Object): Reference to the object to move to. This
                can also be an exit object, in which case the
                destination property is used as destination.
            quiet (bool): If true, turn off the calling of the emit hooks
                (announce_move_to/from etc)
            emit_to_obj (Object): object to receive error messages
            use_destination (bool): Default is for objects to use the "destination"
                 property of destinations as the target to move to. Turning off this
                 keyword allows objects to move "inside" exit objects.
            to_none (bool): Allow destination to be None. Note that no hooks are run when
                 moving to a None location. If you want to run hooks, run them manually
                 (and make sure they can manage None locations).
            move_hooks (bool): If False, turn off the calling of move-related hooks
                (at_before/after_move etc) with quiet=True, this is as quiet a move
                as can be done.

        Keyword Args:
          Passed on to announce_move_to and announce_move_from hooks.

        Returns:
            result (bool): True/False depending on if there were problems with the move.
                    This method may also return various error messages to the
                    `emit_to_obj`.

        Notes:
            No access checks are done in this method, these should be handled before
            calling `move_to`.

            The `DefaultObject` hooks called (if `move_hooks=True`) are, in order:

             1. `self.at_before_move(destination)` (if this returns False, move is aborted)
             2. `source_location.at_object_leave(self, destination)`
             3. `self.announce_move_from(destination)`
             4. (move happens here)
             5. `self.announce_move_to(source_location)`
             6. `destination.at_object_receive(self, source_location)`
             7. `self.at_after_move(source_location)`

        """

        def logerr(string="", err=None):
            """Simple log helper method"""
            logger.log_trace()
            self.msg("%s%s" % (string, "" if err is None else " (%s)" % err))
            return

        errtxt = _("Couldn't perform move ('%s'). Contact an admin.")
        if not emit_to_obj:
            emit_to_obj = self

        if not destination:
            if to_none:
                # immediately move to None. There can be no hooks called since
                # there is no destination to call them with.
                self.location = None
                return True
            emit_to_obj.msg(_("The destination doesn't exist."))
            return False
        if destination.destination and use_destination:
            # traverse exits
            destination = destination.destination

        # Before the move, call eventual pre-commands.
        if move_hooks:
            try:
                if not self.at_before_move(destination):
                    return False
            except Exception as err:
                logerr(errtxt % "at_before_move()", err)
                return False

        # Save the old location
        source_location = self.location

        # Call hook on source location
        if move_hooks and source_location:
            try:
                source_location.at_object_leave(self, destination)
            except Exception as err:
                logerr(errtxt % "at_object_leave()", err)
                return False

        if not quiet:
            # tell the old room we are leaving
            try:
                self.announce_move_from(destination, **kwargs)
            except Exception as err:
                logerr(errtxt % "at_announce_move()", err)
                return False

        # Perform move
        # set pose time to 0 and observer mode to False
        self.set_pose_time(0.0)
        self.set_obs_mode(False)
        try:
            self.location = destination
        except Exception as err:
            logerr(errtxt % "location change", err)
            return False

        if not quiet:
            # Tell the new room we are there.
            try:
                self.announce_move_to(source_location, **kwargs)
            except Exception as err:
                logerr(errtxt % "announce_move_to()", err)
                return False

        if move_hooks:
            # Perform eventual extra commands on the receiving location
            # (the object has already arrived at this point)
            try:
                destination.at_object_receive(self, source_location)
            except Exception as err:
                logerr(errtxt % "at_object_receive()", err)
                return False

        # Execute eventual extra commands on this object after moving it
        # (usually calling 'look')
        if move_hooks:
            try:
                self.at_after_move(source_location)
            except Exception as err:
                logerr(errtxt % "at_after_move", err)
                return False
        return True

    pass
