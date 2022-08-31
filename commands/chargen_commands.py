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
        # TODO: Check if a art of the same name already exists and, if so, modify it instead of creating a new one.
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
        # Set the baseline AP cost for an art at 15.
        true_ap_change = -15
        if len(art_list) == 4:
            effects = art_list[3]
            # Split up the effects at the space bar.
            split_effects = effects.split()
            # Now, for each effect in the split_effects list, confirm that it is in EFFECTS.
            # If so, modify the art's AP cost based on the data in EFFECTS.
            ex_move = False
            for art_effect in split_effects:
                effect_ok = False
                for real_effect in EFFECTS:
                    if art_effect in real_effect.name:
                        effect_ok = True
                        true_ap_change += int(real_effect.ap_change)
                    if real_effect.name == "EX":
                        ex_move = True
                if not effect_ok:
                    return caller.msg("Error: at least one of your Effects is not a valid Effect.")
            # Having confirmed the Art is well-formed, add it to the character's list of Arts.
            # Check if it is regular Art (120 points between Damage/Acc) or EX (140 points).
            if ex_move:
                new_art = Attack(name, true_ap_change, damage_int, (140 - damage_int), base_stat, split_effects)
            else:
                new_art = Attack(name, true_ap_change, damage_int, (120 - damage_int), base_stat, split_effects)
        else:
            new_art = Attack(name, true_ap_change, damage_int, (120 - damage_int), base_stat)
        caller.db.arts.append(new_art)
        caller.msg("{0} has been added to your list of Arts.".format(name))

class CmdChargen(default_cmds.MuxCommand):
    """
        A character generation command used to set your five stats: Power,
        Knowledge, Parry, Barrier, and Speed. The total must be equal to
        your character's Stat Total. By default, this is 625, or 125 per stat.

        Remember to place commas and spaces between each stat assignment.

        Usage:
          +chargen <power>, <knowledge>, <parry>, <barrier>, <speed>

    """

    key = "+chargen"
    aliases = ["chargen"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args
        split_args = args.split(", ")
        # Check and make sure the result is a list that's five entries long.
        if not len(split_args) == 5:
            return caller.msg("Please input five stats, separated by a comma and a space.")
        # Loop through the list to turn the inputs into integers and sum up the total.
        split_args_sum = 0
        for i in split_args:
            split_args_sum += int(i)
        # For now, all player characters will have a Stat Total of 625.
        stat_total = 625
        # Compare the sum of the input numbers with the Stat Total.
        if split_args_sum != stat_total:
            return caller.msg("Please ensure your total stat value is equal to {0}.".format(stat_total))
        # Make sure that no stat is above 255.
        for stat in split_args:
            if int(stat) > 255:
                return caller.msg("Please ensure that no stat is above the maximum of 255.")
        # Set the stats accordingly.
        caller.db.power = int(split_args[0])
        caller.db.knowledge = int(split_args[1])
        caller.db.parry = int(split_args[2])
        caller.db.barrier = int(split_args[3])
        caller.db.speed = int(split_args[4])
        caller.msg("Your stats have been set. Confirm them with +sheet.")
