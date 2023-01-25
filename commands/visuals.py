"""
Visuals Commands

Visuals Commands are associated with the game's presentation (e.g., highlighting character names in poses with
Posecolors).

"""
import re

from evennia import default_cmds
from world.utilities.utilities import logger


class CmdPoseColors(default_cmds.MuxCommand):
    """
    Toggle colored names in poses. Posecolors/self and
    posecolors/others are used to set the colors of one's
    own name and other names, respectively. Type "color
    xterm256" to see the list of eligible color codes.

    Usage:
      posecolors on/off
      posecolors/self <xterm256 code>
      posecolors/others <xterm256 code>

    Examples:
      posecolors on
      posecolors/self 555
      posecolors/others 155

    """

    key = "posecolors"
    aliases = "+posecolors"
    switch_options = ("self", "others")
    locks = "cmd:all()"

    def func(self):
        """Changes pose colors"""

        caller = self.caller
        args = self.args
        switches = self.switches

        if switches or args:
            if args == "on":
                caller.db.pose_colors_on = True
                caller.msg("Name highlighting enabled")
            elif args == "off":
                caller.db.pose_colors_on = False
                caller.msg("Name highlighting disabled")
            elif "self" in switches:
                if len(args) == 3 and args.isdigit:
                    caller.db.pose_colors_self = str(args)
                    caller.msg("Player's name highlighting color updated")
            elif "others" in switches:
                if len(args) == 3 and args.isdigit:
                    caller.db.pose_colors_self = str(args)
                    caller.msg("Other's name highlighting color updated")
            else:
                caller.msg("Unknown switch/argument!")
                return


class CmdPoseHeaders(default_cmds.MuxCommand):
    """
    Toggle pose headers, which inform you who has posed
    whenever the @emit command is used.

    Usage:
      poseheaders on/off

    """

    key = "poseheaders"
    aliases = "+poseheaders"
    locks = "cmd:all()"

    def func(self):
        """Changes pose headers"""

        caller = self.caller
        args = self.args

        if args:
            if args == "on":
                caller.db.pose_headers_on = True
                caller.msg("Pose headers enabled.")
            elif args == "off":
                caller.db.pose_headers_on = False
                caller.msg("Pose headers disabled.")
        else:
            caller.msg("Command not recognized. Please input on or off as an argument.")