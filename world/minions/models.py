from django.db import models
from world.arts.models import Arts


class Minion(models.Model):
    name = models.CharField(
        'Name of template for minion, defined in advance in the Minions database table',
        max_length=255,
        blank=False,
        null=False
    )
    lf = models.IntegerField(
        'LF',
        default=1000
    )
    maxlf = models.IntegerField(
        'Max LF',
        default=1000
    )
    ap = models.IntegerField(
        'Starting AP',
        default=50
    )
    maxap = models.IntegerField(
        'Max AP',
        default=100
    )
    ex = models.IntegerField(
        'Starting EX',
        default=0
    )
    maxex = models.IntegerField(
        'Max EX',
        default=100
    )
    power = models.IntegerField(
        'Power',
        default=125
    )
    knowledge = models.IntegerField(
        'Knowledge',
        default=125
    )
    parry = models.IntegerField(
        'Parry',
        default=125
    )
    barrier = models.IntegerField(
        'Barrier',
        default=125
    )
    speed = models.IntegerField(
        'Speed',
        default=125
    )
    # arts attributed to minions
    arts = models.ManyToManyField(
        Arts,
        blank=True,
        null=False,
        related_name="arts")