from django.views.generic import DetailView, ListView
from world.events.models import RPEvent

class MyFirstViewClass(ListView):
    model = RPEvent
    template_name = "events/test.html"

    # def get_context_data(self, **kwargs):
    #     context = super(MyFirstViewClass, self).get_context_data(**kwargs)
    #     return context