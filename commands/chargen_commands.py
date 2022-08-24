from evennia import default_cmds
from world.combat.effects import EFFECTS
from world.combat.attacks import Attack

class CmdAddArt(default_cmds.MuxCommand):
    """
        A character generation command that adds an Art to
        your character's list of Arts. Specify its name, Damage,
        Base Stat (Power or Knowledge), and Effects.

        Name, Damage, Base Stat, and Effects should be separated by
        commas. Different Effects should be separated by spaces.

        Usage:
          +addart <name of art>, <damage>, <base stat>, <effect1> <effect2>

    """

    key = "+addart"
    aliases = ["addart"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args
        # Create a list of Arts if the character does not yet have one.
        if not caller.db.arts:
            caller.db.arts = []
        # Name = string, damage = int, base stat = string, effects = string(s).
        # Check that there are args.
        if not args:
            return caller.msg("You must provide a name, damage value, base stat, and effects (if any).")
        # Split the args at the commas.
        art_list = args.split(", ")
        name = art_list[0]
        if not isinstance(name, str):
            return caller.msg("Error: the name of your Art must be a string.")
        damage = art_list[1]
        damage_int = int(damage)
        if damage_int not in range(0, 100):
            return caller.msg("Error: your damage value must be an integer between 0 and 100.")
        base_stat = art_list[2]
        # Checking that the base stat is either Power or Knowledge.
        if base_stat.lower() not in ["power", "knowledge"]:
            return caller.msg("Error: your Art's base stat must be either Power or Knowledge.")
        effects = art_list[3]
        # Split up the effects at the space bar.
        split_effects = effects.split()
        # Now, for each effect in the split_effects list, confirm that it is in EFFECTS.
        for art_effect in split_effects:
            effect_ok = False
            for real_effect in EFFECTS:
                if art_effect in real_effect.name:
                    effect_ok = True
            if not effect_ok:
                return caller.msg("Error: at least one of your Effects is not a valid Effect.")
        # Having confirmed the Art is well-formed, add it to the character's list of Arts.
        new_art = Attack(name, damage, (100 - int(damage)), base_stat, split_effects)
        caller.db.arts.append(new_art)
        caller.msg("{0} has been added to your list of Arts.".format(name))