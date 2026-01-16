from django.db import models
from world.arts.models import Arts


# Create your models here.
class Aspect(models.Model):
    # characters who have this Aspect
    characters = models.ManyToManyField(
        "objects.ObjectDB",
        related_name="aspects",
        blank=True)

    name = models.TextField(
        'Aspect name',
        default='Default aspect name'
    )

    cost = models.IntegerField(
        'Capacity cost of Aspect',
        default=0,
        blank=True,
    )

    linked_art = models.ForeignKey(
        Arts,
        related_name="aspects",
        default=None,
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )