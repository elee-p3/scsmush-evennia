from django.shortcuts import render
from world.aspects.models import Aspect


# Create your views here.
def aspects(request):
    all_aspects = Aspect.objects.all()
    context = { "all_aspects": all_aspects }
    return render(request, "aspect/aspect.html", context)