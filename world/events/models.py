from datetime import datetime, timedelta

from evennia.utils.idmapper.models import SharedMemoryModel
from django.db import models
from django.db.models import Q, QuerySet
from django.urls import reverse

# from .managers import OrganizationManager, LandManager, RPEventQuerySet
# from server.utils.arx_utils import (
#     get_week,
#     inform_staff,
#     CachedProperty,
#     CachedPropertiesMixin,
#     classproperty,
#     a_or_an,
#     inform_guides,
#     commafy,
#     get_full_url,
# )


class RPEvent(SharedMemoryModel):
    """
    A model to store RP events created by either players or GMs. We use the PlayerOrNpc
    model instead of directly linking to players so that we can have npcs creating
    or participating in events in our history for in-character transformations of
    the event into stories. Events can be public or private, and run by a gm or not.
    Events can have money tossed at them in order to generate prestige, which
    is indicated by the celebration_tier.
    """

    db_name = models.CharField(max_length=255, db_index=True)
    db_desc = models.TextField(blank=True, null=True)
    db_location = models.ForeignKey(
        "objects.ObjectDB",
        blank=True,
        null=True,
        related_name="events_held",
        on_delete=models.SET_NULL,
    )
    db_date = models.DateTimeField(blank=True, null=True)
    db_finished = models.BooleanField(default=False)
    db_results = models.TextField(blank=True, null=True)
    db_room_desc = models.TextField(blank=True, null=True)
    db_participants = models.TextField(blank=True, null=True) # This will be a comma-separated list of character names

    # def create_room(self):
    #     """Creates a temp room for this RPEvent's plotroom"""
    #     if self.location:
    #         return
    #
    #     if self.plotroom is None:
    #         return
    #
    #     self.location = self.plotroom.spawn_room()
    #     self.save()
    #     return
    #
    # def clear_room(self):
    #     """Gets rid of a temp room"""
    #     if self.plotroom is None:
    #         return
    #
    #     if self.location is None:
    #         return
    #
    #     self.location = None
    #     self.save()
    #     return

    @property
    def location_name(self):
        if self.plotroom:
            return self.plotroom.ansi_name()
        elif self.location:
            return self.location.key
        else:
            return ""

    def display(self):
        """Returns string display for event"""
        msg = "{wName:{n %s\n" % self.name
        msg += "{wHosts:{n %s\n" % ", ".join(str(ob) for ob in self.hosts.all())
        msg += "{wLocation:{n %s\n" % self.location_name
        msg += "{wDate:{n %s\n" % self.date.strftime("%x %H:%M")
        msg += "{wDesc:{n\n%s\n" % self.desc
        # msg += "{wEvent Page:{n %s\n" % get_full_url(self.get_absolute_url())
        return msg

    def __str__(self):
        return self.name

    @property
    def hostnames(self):
        """Returns string of all hosts"""
        return ", ".join(str(ob) for ob in self.hosts.all())

    # @property
    # def log(self):
    #     """Returns our logfile"""
    #     try:
    #         from typeclasses.scripts.event_manager import LOGPATH
    #
    #         filename = LOGPATH + "event_log_%s.txt" % self.id
    #         with open(filename) as log:
    #             msg = log.read()
    #         return msg
    #     except IOError:
    #         return ""

    # @property
    # def tagkey(self):
    #     """
    #     Tagkey MUST be unique. So we have to incorporate the ID of the event
    #     for the tagkey in case of duplicate event names.
    #     """
    #     return "%s_%s" % (self.name.lower(), self.id)
    #
    # @property
    # def tagdata(self):
    #     """Returns data our tag should have"""
    #     return str(self.id)
