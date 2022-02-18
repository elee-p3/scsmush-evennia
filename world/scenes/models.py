from django.db import models

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

    # Add the given log_text to the scene's corresponding Log object. If said log
    # does not yet exist, one is created and the text is added to it.
    def addLogText(self, log_text):
        if not hasattr(self, 'log'):
            log = Log(content="")
            log.scene = self
            log.save()
        
        log = self.log
        log.content += log_text + "\n"
        log.save()


# Contains the complete log of every participant interaction throughout the lifetime
# of a parent Scene.
class Log(models.Model):
    # Stores relationship to parent scene.
    scene = models.OneToOneField(
        Scene,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    # The actual text content of the log (a concatenation of all poses during the
    # course of the event).
    content = models.TextField()
