from evennia import default_cmds
from world.minions.models import Minion
from typeclasses.characters import Character
import random
import string

class CmdCreateMinion(default_cmds.MuxCommand):
    """
        Create a minion template

        Usage:
          createminion

        Creates a minion template. The user will be prompted to input information field by field, and will confirm their
        input by pressing enter.

        There will be a final confirmation before the minion template is added.
        """
    key = "newminion"
    lock = "cmd:all()"
    help_category = "General"

    def func(self):
        caller = self.caller
        name = yield("Minion template name?")
        max_lf = yield("Max LF?")
        max_ap = yield("Max AP?")
        max_ex = yield("Max EX?")
        power = yield("Power?")
        knowledge = yield("Knowledge?")
        parry = yield("Parry?")
        barrier = yield("Barrier?")
        speed = yield("Speed?")
        arts = []
        art = "waiting for input" # this value will never be used - it's just so the while loop doesn't immediately fail
        art_counter = 0

        while art and (art_counter <= 10):
            art = yield("""
            Input an art. This will take the same format as setart, i.e. <name of art>, <damage>, <base stat>, <effect1> <effect2>
            To finish the minion creation process, simply press enter with no input.""")
            arts.append(art)
            art_counter += 1
            if art:
                caller.msg("Art added.")

        arts_display_string = ""
        arts_final_string = ""
        for art in arts:
            arts_display_string += art + "\n      "
            arts_final_string += art + ","

        y_or_n = None
        while (y_or_n != "y") and (y_or_n != "n"):
            y_or_n = yield("""Template name: {name}
            LF: {lf}
            AP: {ap}
            EX: {ex}
            Power: {power}
            Knowledge: {knowledge}
            Parry: {parry}
            Barrier: {barrier}
            Speed: {speed}
            Arts: {arts}
            
            Confirm that the template looks correct (y/n): """.format(name=name,
                                                                      lf=max_lf,
                                                                      ap=max_ap,
                                                                      ex=max_ex,
                                                                      power=power,
                                                                      knowledge=knowledge,
                                                                      parry=parry,
                                                                      barrier=barrier,
                                                                      speed=speed,
                                                                      arts=arts_display_string))

        if y_or_n == "n":
            caller.msg("Minion template creation cancelled.")
            return

        Minion.objects.create(name=name,
                              maxlf=max_lf,
                              maxap=max_ap,
                              maxex=max_ex,
                              power=power,
                              knowledge=knowledge,
                              parry=parry,
                              barrier=barrier,
                              speed=speed,
                              arts=arts_final_string)

        caller.msg("Minion template added!")


class CmdTest(default_cmds.MuxCommand):
    """
    some stuff
    """

    key = "test"
    locks = "cmd:all()"

    def func(self):
        random_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        Character.create(random_name,
                         location=self.caller.location)
        created_char = next(x for x in self.caller.location.contents_get(content_type="character") if x.name == random_name)
        created_char.db.sex = "Female"
        created_char.db.maxlf = 20000
        self.caller.msg(f"Created #{created_char.name}")

class CmdDel(default_cmds.MuxCommand):
    key = "deltron"
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        input_name = self.args
        char = next(x for x in self.caller.location.contents_get(content_type="character") if x.name == input_name)
        char.delete()
        caller.msg(f"Deleted #{input_name}")