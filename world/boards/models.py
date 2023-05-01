import logging
from django.db import models

# Board (aka "message board" aka "bulletin board" aka "bboard") is a model representing
# a single board/topic within SCSMUSH's bulletin board system.
#
# Boards are flat (non-hierarchical) and all represent top-level topics within the system.
#
# Each board can have many Posts within it, and has a strict ownership relationship over its
# posts.
class Board(models.Model):
    # The name/title of the bulletin board shown to the user.
    name = models.CharField(null=False, blank=True, max_length=256)

    # The description of the board shown to the user. The intent is for this to
    # be short (1-2 sentences), but it was encoded as a TextField to avoid having to
    # bother with error handling on content length.
    description = models.TextField(null=False, blank=True)

    # The set of characters who are subscribed to this board.
    # TODO(daniel): add validation that this is only ever set with characters.
    subscribers = models.ManyToManyField(
        "objects.ObjectDB",
        blank=True,
        related_name="subscribed_boards",
    )


# A Post is a single announcement, message, article, etc. that is posted to a parent
# Board (above). Posts are strictly owned by their parent Board: they cannot be included
# in multiple Boards.
class Post(models.Model):
    # Title of the post shown to the user.
    title = models.CharField(max_length=256)

    # The body (contents) of the post represented in Evennia markdown #becauseEvennia.
    # This content will be formatted prior to display to the user.
    body = models.TextField(null=False, blank=True)

    # Parent Board to which this Post is posted.
    board = models.ForeignKey(
        Board,
        blank=True,
        null=True,
        related_name="posts",
        on_delete=models.CASCADE)
    
    # The character responsible for authoring this messageboard post.
    # TODO(daniel): add validation so that only Characters can be set here.
    author = models.ForeignKey(
        "objects.Character",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    # Representing post read (past tense "red" not present tense "reed") status
    # via presence of a join relationship between a character and a post that they
    # have read. Presence of `post` in `character.posts_read` indicates that
    # `character` has read `post`. Conversely, `post.readers` contains all characters
    # who have read `post`.
    # TODO(daniel): add valiation so that only Characters can be set here.
    readers = models.ManyToManyField(
        "objects.ObjectDB",
        related_name="posts_read",
        blank=True)

    created_at = models.DateTimeField(null=False, auto_now_add=True)
    updated_at = models.DateTimeField(null=False, auto_now=True)

    # Given an instance of Character, returns true if the given Character has
    # read this post.
    def was_read_by(self, character):
        matching_characters = self.readers.filter(pk=character.id)
        if matching_characters.len() > 1 or matching_characters.len() <0:
            logger = logging.getLogger("django.request")
            logger.error("Post#was_read_by() found multiple instances of a read for one character")
        return self.readers.filter(pk=character.id).len() == 1

