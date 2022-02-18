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
    start_time = models.DateTimeField('Scene start time')
    end_time = models.DateTimeField('Scene end time')

    # Hosting location for the current scene. Location references a "room"
    # ObjectDB model in underlying evennia.
    location = models.ForeignKey(
        "objects.ObjectDB",
        blank=True,
        null=True,
        related_name="scenes",
        on_delete=models.SET_NULL,
    )

    # Record of all participants that took part in the scene SO FAR. As new
    # participants join the scene, they should be added here as well.
    participants = models.ManyToManyField(
        "objects.ObjectDB",
        blank=True,
        null=True,
        related_name="scenes",
    )

# Contains the complete log of every participant interaction throughout the lifetime
# of a parent Scene.
class Log(models.Model):
    # Stores relationship to parent scene.
    scene = models.ForeignKey(
        Scene,
        blank=True,
        null=True,
        related_name="log",
        on_delete=models.SET_NULL,
    )

    # The actual text content of the log (a concatenation of all poses during the
    # course of the event).
    content = models.TextField()
