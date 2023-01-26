from django.db import models

class Board(models.Model):
    name = models.CharField(max_length=256)
    