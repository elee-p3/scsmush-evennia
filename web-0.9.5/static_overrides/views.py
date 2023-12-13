from evennia.web.website.views import *

class CharacterListView(LoginRequiredMixin, CharacterMixin, ListView):
    """
        This view provides a mechanism by which a logged-in player can view a list
        of all other characters.

        This view requires authentication by default as a nominal effort to prevent
        human stalkers and automated bots/scrapers from harvesting data on your users.

        """

    # -- Django constructs --
    template_name = "website/character_list.html"
    paginate_by = 100

    # -- Evennia constructs --
    page_title = "Character List"
    access_type = "view"

    def get_queryset(self):
        """
        This method will override the Django get_queryset method to return a
        list of all characters (filtered/sorted) instead of just those limited
        to the account.

        Returns:
            queryset (QuerySet): Django queryset for use in the given view.

        """
        account = self.request.user

        # Return a queryset consisting of characters the user is allowed to
        # see.
        ids = [
            obj.id for obj in self.typeclass.objects.all() if obj.access(account, self.access_type)
        ]

        return self.typeclass.objects.filter(id__in=ids).order_by(Lower("db_key"))


    def get_context_data(self, **kwargs):
        context = super(CharacterListView, self).get_context_data(**kwargs)

        account = self.request.user

        account_list = type(account).objects.all()
        # account_list = self.typeclass.objects.all()
        guest_list = []
        player_list = []
        admin_list = []

        for account in account_list:
            if len(account.db_tags.all()) > 1:
                if account.db_tags.all()[1].db_key == 'developer':
                    admin_list.append(account.name)
                elif account.db_tags.all()[1].db_key == 'guest':
                    guest_list.append(account.name)
            else:
                player_list.append(account.name)

        context['guest_list'] = guest_list
        context['player_list'] = player_list
        context['admin_list'] = admin_list
        context['test'] = 'my test string'

        # context = {
        #     'guest_list': guest_list,
        #     'player_list': player_list,
        #     'admin_list': admin_list
        # }

        return context
