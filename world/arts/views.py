from django.shortcuts import render
from world.arts.models import Arts

# Create your views here.
def arts(request):
    all_arts = Arts.objects.all()
    context = { "all_arts": all_arts }
    return render(request, "arts/arts.html", context)