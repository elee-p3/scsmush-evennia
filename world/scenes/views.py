from world.scenes.models import Scene
from django.shortcuts import get_object_or_404, render

def detail(request, scene_id):
    scene = get_object_or_404(Scene, pk=scene_id)
    context = {
        "scene": scene,
        "user": request.user
    }
    return render(request, "scenes/detail.html", context)


def scenes(request):
    all_scenes = Scene.objects.all()
    context = { "all_scenes": all_scenes }
    return render(request, "scenes/scenes.html", context)