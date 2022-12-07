from django.db import models
from django.urls import reverse

# Represents one RP scene or "event".
#
# Scenes occur in only one location, and only one scene can occur in a
# given location at a given time.
class Scene(models.Model):
    # Scene start and end times to be set automatically by the @event/start
    # and @event/end commands.
    # 
    # Start time can be in the future, indicating that the event is scheduled
    # but has not yet started.
    #
    # End time can be null, and that indicates that the event is still un-ended.
    start_time = models.DateTimeField(
        'Scene start time',
        blank=True,
        null=True)
    end_time = models.DateTimeField(
        'Scene end time',
        blank=True,
        null=True)

    # A human-readable title / display name for the scene. Purely for hoomaahns.
    name = models.CharField(
        'Scene display name',
        max_length=255,
        blank=True,
        null=True)

    # A human-readable description of the scene. Used to set up the context and
    # setting in which the scene takes place.
    description = models.TextField(
        'Scene description',
        blank=True,
        null=True)

    # Hosting location for the current scene. Location references a "room"
    # ObjectDB model in underlying evennia.
    location = models.ForeignKey(
        "objects.ObjectDB",
        blank=True,
        null=True,
        related_name="scenes_at_location",
        on_delete=models.SET_NULL,
    )

    # Record of all participants that took part in the scene SO FAR. As new
    # participants join the scene, they should be added here as well.
    participants = models.ManyToManyField(
        "objects.ObjectDB",
        blank=True,
        related_name="scenes_participated",
    )

    # Given the type of a game entry (expects LogEntry.EntryType), the contents of the
    # entry, and the character responsible, creates a corresponding new log entry and
    # attaches to this scene.
    def addLogEntry(self, type, text_content, character):
        self.logentry_set.create(
            scene=self,
            content=text_content,
            type=type,
            character=character
        )

    def web_get_detail_url(self):
        return reverse('scenes:detail', kwargs={'scene_id': self.id})


# Contains the complete log of every participant interaction throughout the lifetime
# of a parent Scene.
class LogEntry(models.Model):
    # Stores relationship to parent scene.
    scene = models.ForeignKey(
        Scene,
        blank=True,
        null=True,
        on_delete=models.CASCADE)

    # The actual text content of the log (a concatenation of all poses during the
    # course of the event).
    content = models.TextField()

    # Automatically note the creation time when the model is first saved.
    created_at = models.DateTimeField(auto_now_add=True)

    # An enum allowing us to keep track of the different types of entries. This will be
    # used to determine what the presentation should be (if necessary). In the future,
    # may also be used to figure out which additional/optional fields are use, should we
    # add per-type fields.
    # class EntryType(models.IntegerChoices):
    #    EMIT = 1
    #    SAY = 2
    #    POSE = 3
    #    DICE = 4
    class EntryType(models.IntegerField):
        EMIT = 1
        SAY = 2
        POSE = 3
        DICE = 4
        COMBAT = 5
        TYPE_CHOICES = (
            (EMIT, 'Emit'),
            (SAY, 'Say'),
            (POSE, 'Pose'),
            (DICE, 'Dice'),
            (COMBAT, 'Combat')
        )

    # The type of operation captured in this log entry (see EntryType).
    type = models.IntegerField(
        choices=EntryType.TYPE_CHOICES
    )

    # The character responsible for this particularly heinous activity.
    character = models.ForeignKey(
        "objects.ObjectDB",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )