from django.shortcuts import render
from world.aspects.models import LinkedAspect


# Create your views here.
def aspects(request):
    all_aspects = LinkedAspect.objects.all()
    context = { "all_aspects": all_aspects }
    return render(request, "aspect/aspect.html", context)