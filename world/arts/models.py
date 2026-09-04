from django.db import models

class Art(models.Model):
    # characters who use this art
    characters = models.ManyToManyField(
        "objects.ObjectDB",
        related_name="art")

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

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, str):
            return self.name.lower() == other.lower()
        elif isinstance(other, Art):
            return self.name.lower() == other.name.lower()