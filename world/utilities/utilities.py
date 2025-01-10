from evennia.objects.models import ObjectDB


def location_character_search(location):
    location_objects = location.contents
    characters = []
    for obj in location_objects:
        if "Character" in obj.db_typeclass_path:
            characters.append(obj)
    return characters


def logger(caller, message, level="info"):
    # This is for administrative logging and debugging purposes. Not to be confused with the Scenes system or LogEntry.
    if level == "info":
        caller.msg("|yINFO:|n " + message)
    # We're just putting in this if/else statement provisionally for when we implement more involved debug logging.
    else:
        caller.msg("|cDEBUG:|n " + message)


def find_attacker_from_key(attacker_key):
    # This finds the attacker's character object from their key.
    # Because Evennia uses Python's default pickling method, we cannot pass character objects directly into a queue.
    all_objects = ObjectDB.objects.all()
    attacker_queryset = all_objects.filter(db_key=attacker_key)
    attacker = attacker_queryset[0]
    return attacker
