from django.shortcuts import render
from typeclasses.characters import Character

def character(request):
    character_list = Character.objects.all()
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
