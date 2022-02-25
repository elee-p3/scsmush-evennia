from django.http import HttpResponse
from world.scenes.models import Scene
from django.shortcuts import get_object_or_404, render
from django.utils.timezone import localtime

def detail(request, scene_id):
    scene = get_object_or_404(Scene, pk=scene_id)
    participants = list(scene.participants.all())
    context = {
        "scene": scene,
        "participants": participants,
    }
    return render(request, "scenes/detail.html", context)

def scenes(request):
    all_scenes = Scene.objects.all()
    context = { "all_scenes": all_scenes }
    return render(request, "scenes/scenes.html", context)