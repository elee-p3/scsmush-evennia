from django.contrib import admin
from world.scenes.models import Scene, LogEntry


class LogEntryInline(admin.StackedInline):
    model = LogEntry
    extra = 1


class SceneAdmin(admin.ModelAdmin):
    inlines = [LogEntryInline]


admin.site.register(Scene, SceneAdmin)