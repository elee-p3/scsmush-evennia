"""
MUSH Core Commands

MUSH Core Commands are commands generally useful to any MUSH, including +finger and the Pose Order Tracker (POT).

"""
import time
from math import floor, ceil

from evennia.server.sessionhandler import SESSIONS
from evennia import default_cmds
from evennia.utils import utils, evtable
from commands.command import prune_sessions
from world.utilities.utilities import logger


class CmdFinger(default_cmds.MuxCommand):
    """
        +finger
        Usage:
          +finger <character>
        Displays finger'd character's information
        """

    key = '+finger'
    aliases = ["finger", "oocfinger", "+oocfinger"]
    locks = "cmd:all()"

    def func(self):
        if not self.args:
            self.caller.msg("Please specify a character.")
            return

        # We've tried changing the evennia-master code in evennia/objects/object.py to allow for non-exact string
        # matching with global_search=True, but this seems to cause "examine <db_id>" to fail
        # TODO: figure out a way to have partial string matching AND db_id referencing. Might be able to do this with more playing around with the if-else logic in objects.py
        target = self.caller.search(self.args, global_search=True)

        # TODO: actually figure out error handling. Need to be able to differentiate between "ambiguous search" error and "not a character" error
        try:
            client_width = self.client_width()
            char = target.get_abilities()
            charInfoTable = evtable.EvTable(border_left_char="|", border_right_char="|", border_top_char="-",
                                            border_bottom_char=" ", width=client_width)
            charInfoTable.add_column()
            charInfoTable.add_column()
            charInfoTable.add_row("Sex: {0}".format(char["sex"]), "Group: {0}".format(char["group"]))
            charInfoTable.add_row("Race: {0}".format(char["race"]), "Domain: {0}".format(char["domain"]))
            charInfoTable.add_row("Origin: {0}".format(char["origin"]), "Element: {0}".format(char["element"]))

            charDescTable = evtable.EvTable(border="table", border_left_char="|", border_right_char="|",
                                            border_top_char="-",
                                            border_bottom_char="_", width=client_width)
            charDescTable.add_column()
            charDescTable.add_row('"{0}"'.format(char["quote"]))
            charDescTable.add_row("")
            charDescTable.add_row("{0}".format(char["profile"]))

            fingerMsg = ""
            fingerMsg += "/\\" + (client_width - 4) * "_" + "/\\" + "\n"  # top border

            header = ""
            alias_list = [x for x in target.aliases.all() if " " not in x]
            # find all aliases that don't contain spaces (this was to get rid of "An Ivo" or "One Ivo")
            if alias_list:
                alias = min(alias_list, key=len).title()
                header = char["name"] + " (" + alias + ")" + " - " + char["occupation"]
            else:
                header = char["name"] + " - " + char["occupation"]

            left_spacing = " " * ((floor(client_width/2.0) - floor(len(header)/2.0)) - 2) # -2 for the \/
            right_spacing = " " * ((floor(client_width / 2.0) - ceil(len(header) / 2.0)) - 2)  # -2 for the \/
            nameBorder = "\\/" + left_spacing + header + right_spacing + "\\/"
            fingerMsg += nameBorder + "\n"

            charInfoString = charInfoTable.__str__()
            fingerMsg += charInfoString[:charInfoString.rfind('\n')] + "\n"  # delete last newline (i.e. bottom border)
            fingerMsg += charDescTable.__str__() + "\n"
            fingerMsg += "/\\" + (client_width - 4) * "_" + "/\\" + "\n"
            fingerMsg += "\\/" + (client_width - 4) * " " + "\\/" + "\n"

            self.caller.msg(fingerMsg)
        except:
            self.caller.msg("Target is either not a character or there are multiple matches.")


class CmdPot(default_cmds.MuxCommand):
    # Currently, this calls a function defined in command.py.
    """
    View the pose tracker (pot). The pose tracker displays the name,
    time connected, time idle, and time since last posed of every
    character in the room, ordered starting with whomever posed
    longest ago. Thus, during an ongoing scene, the person whose
    turn it is to pose will appear at the top of the list.

    Those who have not posed are listed below all those who have.
    To signify that you are leaving an ongoing scene, type +observe
    to reset your pose timer and move to the bottom (see "help observe").

    Usage:
      +pot

    """

    key = "+pot"
    aliases = ["pot"]
    locks = "cmd:all()"

    # this is used by the parent
    account_caller = True

    def func(self):
        """
        Get all connected accounts by polling session.
        """

        all_sessions = SESSIONS.get_sessions()
        # Not quite sure how a non-puppeted session can exist - need to dig into this
        all_sessions = [session for session in all_sessions if session.puppet is not None]

        all_sessions = sorted(all_sessions, key=lambda o: o.puppet.get_pose_time()) # sort by last posed time
        pruned_sessions = prune_sessions(all_sessions)

        # TODO: replace styled_table with evtable?
        table = self.styled_table(
            "|wCharacter",
            "|wOn for",
            "|wIdle",
            "|wLast posed",
            "|wLF"
        )

        old_session_list = []

        for session in pruned_sessions:
            if not session.logged_in:
                continue

            puppet = session.puppet
            delta_cmd = time.time() - session.cmd_last_visible
            delta_conn = time.time() - session.conn_time
            delta_pose_time = time.time() - puppet.get_pose_time()
            lf = str(int(puppet.db.lf))
            max_lf = str(int(puppet.db.maxlf))

            # If you have been idle for an hour, you are moved to the bottom and your pose timer is hidden.
            if delta_pose_time > 3600:
                old_session_list.append(session)
                continue

            # assuming it's ok to have a static index here since there will always be a puppet, and it will always
            # have a location
            if puppet.location == self.caller.puppet[0].location:
                # logic for setting up pose table
                table.add_row(puppet.key,
                              utils.time_format(delta_conn, 0),
                              utils.time_format(delta_cmd, 1),
                              utils.time_format(delta_pose_time, 1),
                              lf + "/" + max_lf)

        for session in old_session_list:
            puppet = session.puppet
            delta_cmd = time.time() - session.cmd_last_visible
            delta_conn = time.time() - session.conn_time
            lf = str(int(puppet.db.lf))
            max_lf = str(int(puppet.db.maxlf))

            # Changes display depending on if someone has set themselves as an observer or not.
            # assuming it's ok to have a static index here since there will always be a puppet, and it will always
            # have a location
            if puppet.location == self.caller.puppet[0].location:
                if puppet.get_obs_mode() == True:
                    table.add_row("|y" + puppet.key + " (O)",
                                  utils.time_format(delta_conn, 0),
                                  utils.time_format(delta_cmd, 1),
                                  "-",
                                  lf + "/" + max_lf)
                else:
                    table.add_row(puppet.key,
                                  utils.time_format(delta_conn, 0),
                                  utils.time_format(delta_cmd, 1),
                                  "-",
                                  lf + "/" + max_lf)

        self.caller.msg(table)


class CmdObserve(default_cmds.MuxCommand):
    """
        Enter observer mode. This signifies that you are observing,
        and not participating, in a scene. In +pot, you will be
        displayed at the bottom of the list with an "(O)" before
        your name. If you have previously posed, your pose timer
        will also be reset.

        If your character is leaving an ongoing scene, +observe
        will help to  prevent anyone accidentally waiting on a pose
        from you.

        Usage:
          +observe

    """

    key = "+observe"
    aliases = ["observe"]
    locks = "cmd:all()"

    def func(self):
        self.caller.set_pose_time(0.0)
        self.caller.set_obs_mode(True)
        self.msg("Entering observer mode.")
        self.caller.location.msg_contents(
            "|y<SCENE>|n {0} is now an observer.".format(self.caller.name))