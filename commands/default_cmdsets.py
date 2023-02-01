"""
Command sets

All commands in the game must be grouped in a cmdset.  A given command
can be part of any number of cmdsets and cmdsets can be added/removed
and merged onto entities at runtime.

To create new commands to populate the cmdset, see
`commands/command.py`.

This module wraps the default command sets of Evennia; overloads them
to add/remove commands from the default lineup. You can create your
own cmdsets by inheriting from them or directly from `evennia.CmdSet`.

"""

from commands.scs_dice import *
from commands.command import *
from commands.bboards import *
from commands.combat import *
from commands.chargen import *
from commands.event import *
from commands.misc import *
from commands.visuals import *
from commands.mush_core import *
from commands.minions import *


class CharacterCmdSet(default_cmds.CharacterCmdSet):
    """
    The `CharacterCmdSet` contains general in-game commands like `look`,
    `get`, etc available on in-game Character objects. It is merged with
    the `AccountCmdSet` when an Account puppets a Character.
    """

    key = "DefaultCharacter"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #
        self.add(CmdOOC)
        self.add(CmdSCSDice)
        self.add(CmdEmit)
        self.add(CmdSheet)
        self.add(CmdSetDesc)
        self.add(CmdFinger)
        self.add(CmdWho)
        self.add(CmdMail)
        self.add(CmdBBCreate)
        self.add(CmdBBSub)
        self.add(CmdBBUnsub)
        self.add(CmdBBReadOrPost)
        self.add(CmdBBNew)
        self.add(CmdGetUnreadPosts)
        self.add(CmdPose)
        self.add(CmdSay)
        self.add(CmdPot)
        self.add(CmdObserve)
        self.add(CmdEvent)
        self.add(CmdWarp)
        self.add(CmdPoseColors)
        self.add(CmdPage)
        self.add(CmdAttack)
        self.add(CmdQueue)
        self.add(CmdDodge)
        self.add(CmdRoulette)
        self.add(CmdGridscan)
        self.add(CmdBlock)
        self.add(CmdSetArt)
        self.add(CmdArts)
        self.add(CmdListAttacks)
        self.add(CmdChargen)
        self.add(CmdAim)
        self.add(CmdFeint)
        self.add(CmdRestore)
        self.add(CmdPass)
        self.add(CmdEndure)
        self.add(CmdInterrupt)
        self.add(CmdCheck)
        self.add(CmdPoseHeaders)
        self.add(CmdResetCombatFile)
        self.add(CmdRoomDesc)
        self.add(CmdCreateMinion)


class AccountCmdSet(default_cmds.AccountCmdSet):
    """
    This is the cmdset available to the Account at all times. It is
    combined with the `CharacterCmdSet` when the Account puppets a
    Character. It holds game-account-specific commands, channel
    commands, etc.
    """

    key = "DefaultAccount"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #


class UnloggedinCmdSet(default_cmds.UnloggedinCmdSet):
    """
    Command set available to the Session before being logged in.  This
    holds commands like creating a new account, logging in, etc.
    """

    key = "DefaultUnloggedin"

    def at_cmdset_creation(self):
        """
        Populates the cmdset
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #


class SessionCmdSet(default_cmds.SessionCmdSet):
    """
    This cmdset is made available on Session level once logged in. It
    is empty by default.
    """

    key = "DefaultSession"

    def at_cmdset_creation(self):
        """
        This is the only method defined in a cmdset, called during
        its creation. It should populate the set with command instances.

        As and example we just add the empty base `Command` object.
        It prints some info.
        """
        super().at_cmdset_creation()
        #
        # any commands you add below will overload the default ones.
        #