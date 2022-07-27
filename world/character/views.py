from django.shortcuts import render
from evennia import ObjectDB

def character(request):
    character_list = ObjectDB.objects.filter(db_typeclass_path__contains="Character") # filter by Character typeclass, since ObjectDB contains all objects
    guest_list = []
    player_list = []
    admin_list = []

    for character in character_list:
        permissions = character.permissions.all() # get list of permissions strings, as defined by the db_tags with type "permission"
        if "admin" in permissions:
            admin_list.append(character)
        elif "guest" in permissions:
            guest_list.append(character)
        else:
            player_list.append(character)


    context = {
        'guest_list': guest_list,
        'player_list': player_list,
        'admin_list': admin_list
    }

    return render(request, "character/character.html", context)
