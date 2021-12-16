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
    # a beat with a blank desc will be used for connecting us to a Plot before the Event is finished
    #
    # search_tags = models.ManyToManyField(
    #     "character.SearchTag", blank=True, related_name="events"
    # )

    # objects = QuerySet.as_manager()

    # def can_end_or_move(self, player):
    #     """Whether an in-progress event can be stopped or moved by a host"""
    #     dompc = player.Dominion
    #     return (
    #         self.can_admin(player)
    #         or dompc in self.hosts.all()
    #         or dompc in self.gms.all()
    #     )

    # def can_admin(self, player):
    #     """Who can run admin commands for this event"""
    #     if player.check_permstring("builders"):
    #         return True
    #     if self.gm_event:
    #         return False
    #     try:
    #         dompc = player.Dominion
    #         if not dompc:
    #             return False
    #         return dompc == self.main_host
    #     except AttributeError:
    #         return False

    def create_room(self):
        """Creates a temp room for this RPEvent's plotroom"""
        if self.location:
            return

        if self.plotroom is None:
            return

        self.location = self.plotroom.spawn_room()
        self.save()
        return

    def clear_room(self):
        """Gets rid of a temp room"""
        if self.plotroom is None:
            return

        if self.location is None:
            return

        self.location = None
        self.save()
        return

    # @property
    # def hosts(self):
    #     """Our host or main host"""
    #     return self.dompcs.filter(
    #         event_participation__status__in=(
    #             PCEventParticipation.HOST,
    #             PCEventParticipation.MAIN_HOST,
    #         )
    #     )

    # @property
    # def participants(self):
    #     """Any guest who was invited/attended"""
    #     return self.dompcs.filter(
    #         event_participation__status=PCEventParticipation.GUEST
    #     )

    @property
    def gms(self):
        """GMs for GM Events or PRPs"""
        return self.dompcs.filter(event_participation__gm=True)

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

    @property
    def log(self):
        """Returns our logfile"""
        try:
            from typeclasses.scripts.event_manager import LOGPATH

            filename = LOGPATH + "event_log_%s.txt" % self.id
            with open(filename) as log:
                msg = log.read()
            return msg
        except IOError:
            return ""

    @property
    def tagkey(self):
        """
        Tagkey MUST be unique. So we have to incorporate the ID of the event
        for the tagkey in case of duplicate event names.
        """
        return "%s_%s" % (self.name.lower(), self.id)

    @property
    def tagdata(self):
        """Returns data our tag should have"""
        return str(self.id)

    def tag_obj(self, obj):
        """Attaches a tag to obj about this event"""
        obj.tags.add(self.tagkey, data=self.tagdata, category="event")
        return obj


    # def get_absolute_url(self):
    #     """Gets absolute URL for the RPEvent from their display view"""
    #     return reverse("dominion:display_event", kwargs={"pk": self.id})

    # @CachedProperty
    # def attended(self):
    #     """List of dompcs who attended our event, cached to avoid query with every message"""
    #     return list(self.dompcs.filter(event_participation__attended=True))

    def record_attendance(self, dompc):
        """Records that dompc attended the event"""
        del self.attended
        part, _ = self.pc_event_participation.get_or_create(dompc=dompc)
        part.attended = True
        part.save()

    def invite_dompc(self, dompc, field, value, send_inform=True):
        """Invites a dompc to be a host, gm, or guest"""
        part, _ = self.pc_event_participation.get_or_create(dompc=dompc)
        setattr(part, field, value)
        part.save()
        if send_inform:
            self.invite_participant(part)

    def invite_participant(self, participant):
        """Sends an invitation if we're not finished"""
        if not self.finished:
            participant.invite()

    # def make_announcement(self, msg):
    #     from typeclasses.accounts import Account
    #
    #     msg = "{y(Private Message) %s" % msg
    #     guildies = Member.objects.filter(
    #         organization__in=self.orgs.all(), deguilded=False
    #     )
    #     all_dompcs = PlayerOrNpc.objects.filter(
    #         Q(id__in=self.dompcs.all()) | Q(memberships__in=guildies)
    #     )
    #     audience = Account.objects.filter(
    #         Dominion__in=all_dompcs, db_is_connected=True
    #     ).distinct()
    #     for ob in audience:
    #         ob.msg(msg)