from django.views.generic import DetailView
from world.events.models import RPEvent

class MyFirstViewClass(DetailView):
    model = RPEvent
    template_name = "templates/test.html"

    def get_context_data(self, **kwargs):
        context = super(MyFirstViewClass, self).get_context_data(**kwargs)
        return context