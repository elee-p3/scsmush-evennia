from django.db import models
from django.urls import reverse

class Character(models.Model):

    class Meta:
        managed = False

    def web_get_detail_url(self):
        return reverse(
            "character-detail",
            kwargs={"pk": self.pk, "slug": self.name},
        )