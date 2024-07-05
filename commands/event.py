"""
Event Commands

Event commands are associated with the autologger and, eventually, the scene scheduler.

"""
from datetime import datetime

from evennia import default_cmds
from world.scenes.models import Scene
from world.utilities.utilities import logger


class CmdEvent(default_cmds.MuxCommand):
    """
    The @event command is used to log scenes.

    Usage:
            @event/start: Create a scene and begin logging poses in the current room.
            @event/stop: Stop the log currently running in the room.
            @event/info: Display the current log's ID number, name, etc.
            @event/name [string]: Set the current log's name as [string].
            @event/desc [string]: Set the current log's desc as [string].
            @event/resume [int]: Begin logging poses in the current room as a specified preexisting log ID.
    """

    key = "@event"
    aliases = ["event", "@scene", "scene"]
    locks = "cmd:all()"

    def is_running(self):
        # Check that there is a log running.
        caller = self.caller
        is_running = True
        if not caller.location.db.active_event:
            caller.msg("There is no active event running in this room.")
            is_running = False
        return is_running

    def are_args(self):
        # Check that the user has inputted a string.
        caller = self.caller
        are_args = True
        if not self.args:
            caller.msg("Name the log description what?")
            are_args = False
        return are_args

    def find_event(self):
        # Find the scene object that matches the scene/event reference on the
        # location.
        caller = self.caller
        try:
            events = Scene.objects.filter(id=caller.location.db.event_id).get()
        except Exception as original:
            raise Exception("Found zero or multiple Scenes :/") from original
        return events

    def resume_event(self, scene_id):
        # Find the scene object that matches the specified ID number in Scene.objects.
        try:
            events = Scene.objects.filter(id=scene_id).get()
        except Exception as original:
            raise Exception("Found zero or multiple Scenes :/") from original
        return events

    def func(self):
        caller = self.caller

        if not self.switches:
            caller.msg("You must add a switch, like '@event/start' or '@event/stop'.")
            return

        elif "start" in self.switches:
            # Make sure the current room doesn't already have an active event, and otherwise mark it
            if caller.location.db.active_event:
                caller.msg("There is currently an active event running in this room already.")
                return
            caller.location.db.active_event = True
            event = Scene.objects.create(
                name='Unnamed Event',
                start_time=datetime.now(),
                description='Placeholder description of scene plz change k thx bai',
                location=caller.location,
            )

            caller.location.db.event_id = event.id

            self.caller.location.msg_contents("|y<SCENE>|n A log has been started in this room with scene ID {0}.".format(event.id))
            return

        elif "stop" in self.switches:
            # Make sure the current room's event hasn't already been stopped
            if not self.is_running():
                return

            events = self.find_event()

            # Stop the Room's active event by removing the active event attribute.
            Scene.objects.filter(id=caller.location.db.event_id).update(end_time=datetime.now())
            self.caller.location.msg_contents("|y<SCENE>|n A log has been stopped in this room with scene ID {0}.".format(events.id))
            del caller.location.db.active_event
            return

        elif "info" in self.switches:
            if not self.is_running():
                return

            events = self.find_event()

            caller.msg("This event has the following information:\nName = {0}\nDescription = {1}\nLocation = {2}\nID = {3}".format(events.name, events.description, events.location, events.id))

        elif "name" in self.switches:
            if not self.is_running():
                return

            if not self.are_args():
                return

            Scene.objects.filter(id=caller.location.db.event_id).update(name=self.args)
            caller.msg("Scene name set.")

        elif "desc" in self.switches:
            if not self.is_running():
                return

            if not self.are_args():
                return

            Scene.objects.filter(id=caller.location.db.event_id).update(description=self.args)
            caller.msg("Scene description set.")

        elif "resume" in self.switches:
            # Make sure there is no scene already running when you try to resume one
            if caller.location.db.active_event:
                caller.msg("There is currently an active event running in this room already.")
                return
            if not self.args:
                caller.msg("Please specify a scene ID, which individuates each log's URL, to resume.")
            event = self.resume_event(self.args)
            caller.location.db.active_event = True
            caller.location.db.event_id = event.id

            self.caller.location.msg_contents(
                "|y<SCENE>|n A log has been resumed in this room with scene ID {0}.".format(event.id))
            return