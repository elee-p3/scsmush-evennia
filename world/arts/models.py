from django.db import models
from world.combat.attacks import Attack

class Arts(models.Model):
    # characters who use this art
    characters = models.ManyToManyField(
        "objects.ObjectDB",
        related_name="arts")

    name = models.TextField(
        'Art name',
        default='Default art name'
    )

    ap = models.IntegerField(
        'AP cost of art',
        default=0,
        blank=True,
    )

    dmg = models.IntegerField(
        'Damage of art',
        default=0,
        blank=True
    )

    acc = models.IntegerField(
        'Accuracy of art',
        default=0,
        blank=True
    )

    stat = models.TextField(
        'Main stat, either Power or Knowledge',
        default='Power'
    )

    # it may or may not be worth converting effects to its own model so that we're
    # not just parsing a space-separated string
    effects = models.TextField(
        'Additional art effects',
        default='',
        blank=True,
    )

    isNormal = models.BooleanField(
        'States if this art is a normal',
        default=False,
        blank=True
    )

    @classmethod
    def addArt(cls, art: Attack, is_normal=False):
        Arts.objects.create(
            name=art.name,
            ap=art.ap_change,
            dmg=art.dmg,
            acc=art.acc,
            stat=art.base_stat,
            effects=' '.join(art.effects),
            isNormal=is_normal
        )

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name.lower() == other.lower()
        elif isinstance(other, Arts):
            return self.name.lower() == other.name.lower()