from django.db import models

class Board(models.Model):
    name = models.CharField(max_length=256)

class Post(models.Model):
    title = models.CharField(max_length=256)
    body = models.TextField(null=False, blank=True)

    board = models.ForeignKey(
        Board,
        blank=True,
        null=True,
        related_name="posts",
        on_delete=models.CASCADE)

    created_at = models.DateTimeField(null=False, auto_now_add=True)
    updated_at = models.DateTimeField(null=False, auto_now=True)
