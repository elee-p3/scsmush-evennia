from evennia import ObjectDB, default_cmds
from typeclasses.characters import Character
from world.scenes.models import Scene, LogEntry

# This is a script for a "logmuncher," meant to process RP logs stored as text into Scene objects in the database.
# It will be used to upload logs made prior to the creation of the Scenes model, and can be used later if, e.g.,
# someone forgets to start the autologger to record a scene and so copies the client contents to text instead.

# Logs stored as text have a few issues that the logmuncher will have to deal with:
# 1) There's a bunch of junk text unrelated to the poses in the text logs, like OOC chatter, other commands, etc.
# 2) The character posing may not be obvious (e.g., their name is not automatically at the top of their pose).
# 3) For players other than the one logging, text tags for indenting and linespacing will be missing.
# For simplicity, I'll clean out 1 manually and mark 2 in all caps to distinguish character names from other lines.

# I'll also set the Scene parameters manually, because there's only a few and parsing them as different from
# the LogEntries is unnecessarily complicated given my limited coding skills. I'll start each LogEntry with a single
# word in all caps, which will be part of the posing character's name, and I'll check for it with isupper().
# This will mark a new LogEntry. I'll end the file with "END," to make sure that the last LogEntry is saved.


class CmdLogmunch(default_cmds.MuxCommand):
    """
    The logmuncher is an admin-only command that converts a text file into a Scenes object.
    Used to convert logs that pre-existed the Scenes model into the current format.

    If this works, may upgrade into a system that users can use, in case, e.g., someone
    forgets to @event/start when having a scene.
    """

    key = "logmunch"
    aliases = ["logmuncher"]
    locks = "cmd:perm(Admin)"

    def func(self):
        caller = self.caller
        # First, get the log. I'm new to this, so I'll just put a single text file in the same directory.
        premunched_log = open(".\commands\log.txt", "r")
        caller.msg("Opening premunched_log.")
        # Split up the text by line breaks.
        munched_log = []
        for line in premunched_log:
            if line == "\n":
                # Remove stray newlines for consistent spacing.
                continue
            else:
                munched_log.append(line)
        caller.msg("Munched log appended line by line.")
        # Given how Python's open function works, this should turn the text file into a list, split line by line.
        new_scene = Scene.objects.create(
                    name="Munched Log, Please Change",
                    description="Munched Log, Please Change, thank youuuuuuuu"
                    )
        caller.msg("New scene defined.")
        posing_character_name = ""
        entering_log = False
        log_entry_contents = []
        all_characters = Character.objects.all()
        # Let's try making the default character Headwiz, just so there's never any NoneTypes.
        character = all_characters[0]
        for line in munched_log:
            if line.isupper() and not entering_log:
                # This is the first line of the log, the name of the first poser.
                posing_character_name = line
                entering_log = True
                caller.msg("Character name is now " + posing_character_name)
            elif not line.isupper() and entering_log:
                # This is (part of) the contents of a LogEntry. Adding Evennia newline text tags.
                line += "|/|/"
                log_entry_contents.append(line)
                caller.msg("Line appended.")
            elif line.isupper() and entering_log:
                # This is the end of a log and the start of a new one. First, join the log_contents, adding line breaks.
                new_log_entry = '\n'.join(log_entry_contents)
                # Second, find the Character object from the posing_character_name.
                for obj in all_characters:
                    for_comparison = obj.key.upper()
                    caller.msg("Comparing " + posing_character_name + "to " + for_comparison)
                    if posing_character_name.strip() in for_comparison.strip():
                        character = obj
                        caller.msg("Actual character name is " + obj.key)
                        break
                if not character:
                    # return caller.msg("Error: no character found for a LogEntry. Aborting process.")
                    # Assume that if this is an all caps sentence with no character name, it's another line.
                    # E.g., "EARLIER THAT DAY"
                    line += "|/|/"
                    log_entry_contents.append(line)
                    caller.msg("Line appended.")
                # Most LogEntries will be EMIT, so I'm just gonna declare that and edit it manually when not. Screw you!
                new_scene.addLogEntry(LogEntry.EntryType.EMIT, new_log_entry, character)
                caller.msg("LogEntry appended")
                # Finally, find out if this is the start of a new log entry or the end of the Scene.
                if line != "END":
                    posing_character_name = line
                    log_entry_contents = []
                    caller.msg("Continuing to new logentry. Character name is now " + posing_character_name)
        caller.msg("process complete.")