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

    # The set of accounts who are subscribed to this board.
    subscribers = models.ManyToManyField(
        "accounts.AccountDB",
        blank=True,
        related_name="subscribed_boards",
    )


# A Post is a single announcement, message, article, etc. that is posted to a parent
# Board (above). Posts are strictly owned by their parent Board: they cannot be included
# in multiple Boards.
#
# Note that there is asymmetry between authoring and reading posts:
#  - Posts are AUTHORED by characters, in-universe. This is for fun, creativity, and privacy.
#  - Posts are READ by accounts, i.e., humans IRL. All that matters is whether or not a particular
#    human being has seen a post, not which character they were puppetting at the time.
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
    #
    # Characters are used to keep posts in-universe, and to protect the privacy of the humans
    # behind those characters (who may not want to reveal their account information).
    #
    # TODO(daniel): add validation so that only Characters can be set here.
    author = models.ForeignKey(
        "objects.ObjectDB",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    # `readers` represents post-read (past tense "red" not present tense "reed") status via presence
    # of a join relationship between an ACCOUNT (not a character) and a post that they have read.
    # Presence of `post` in `account.posts_read` indicates that the IRL human associated with
    # `account` has read `post`. Conversely, `post.readers` contains all accounts that have read
    # `post`.
    #
    # As mentioned above, post READS are tracked at the account level (IRL human being), while writes
    # are tracked as actions of a particular puppetted character for in-universe whimsy and privacy.
    readers = models.ManyToManyField(
        "accounts.AccountDB",
        related_name="posts_read",
        blank=True)

    created_at = models.DateTimeField(null=False, auto_now_add=True)
    updated_at = models.DateTimeField(null=False, auto_now=True)

    # Given an instance of Account, returns true if the given Account has read this post.
    def was_read_by(self, account):
        matching_accounts = self.readers.filter(pk=account.id)

        # Per many-to-many.add() semantics, this should never happen.
        if matching_accounts.len() > 1:
            logger = logging.getLogger("django.request")
            logger.error("Post#was_read_by() found multiple instances of a read for one character: #{account.id}")

        return self.readers.filter(pk=account.id).len() == 1

