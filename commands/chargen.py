from evennia import default_cmds
from world.arts.models import Arts
from world.combat.effects import EFFECTS, SUPPORT, DEBUFFS
from world.combat.attacks import Attack


def accuracy_check(accuracy, ex_move=False):
    string = ""
    if ex_move:
        accuracy = accuracy + 2
    if accuracy <= 0:
        string = "Error: your damage value must be an integer between 1 and 11 (or 13 for EX moves). Make sure " \
                 "that your format is: name, damage value, base stat, and effects (if any)."
    return accuracy, string


class CmdSetArt(default_cmds.MuxCommand):
    """
        A character generation command that adds an Art to or
        edits an Art on your character's list of Arts. Specify
        its name, Damage, Base Stat (Power or Knowledge), and Effects.
        Damage must be an integer between 1 and 100.

        Name, Damage, Base Stat, and Effects should be separated by
        commas. Different Effects should be separated by spaces.
        See "help effects" for a list of valid Effects.

        Characters may currently have a maximum of 10 Arts. To remove
        an Art, add the switch /del.

        Usage:
          +setart <name of art>, <damage>, <base stat>, <effect1> <effect2>
          +setart/del <name of art>

    """

    key = "+setart"
    aliases = ["setart"]
    locks = "cmd:all()"


    def func(self):
        # TODO: Check if a art of the same name already exists and, if so, modify it instead of creating a new one.
        caller = self.caller
        args = self.args
        arts = Arts.objects.filter(characters=caller)
        # Create a list of Arts if the character does not yet have one.
        # Name = string, damage = int, base stat = string, effects = string(s).
        if "del" in self.switches:
            art_to_remove = None
            for art in arts:
                if args.lower() == art.name.lower():
                    art_to_remove = art
            if not art_to_remove:
                return caller.msg("Art not found. No Art has been deleted.")
            else:
                caller.delete_art(art_to_remove)
                return
        # Check that there are args.
        if not args:
            return caller.msg("You must provide a name, damage value, base stat, and effects (if any).")
        # Split the args at the commas.
        art_list = args.split(", ")
        name = art_list[0]
        if not isinstance(name, str):
            return caller.msg("Error: the name of your Art must be a string. Make sure that your format is: name, damage"
                              " value, base stat, and effects (if any).")
        damage = art_list[1]
        try:
            damage_int = int(damage)
        except ValueError:
            return caller.msg("Error: your damage value must be an integer. Make sure that your format is: name, damage"
                              " value, base stat, and effects (if any).")
        # Setting a lower bound on damage.
        if damage_int < 1:
            return caller.msg("Error: your damage value must be at least 1.")
        # Base accuracy for Arts will be 12 - damage_int, increased by 2 for EX moves after effects are checked.
        accuracy = 12 - damage_int
        base_stat = art_list[2].lower()
        # Checking that the base stat is either Power or Knowledge.
        if base_stat == "power":
            base_stat = "Power"
        elif base_stat == "knowledge":
            base_stat = "Knowledge"
        else:
            return caller.msg("Error: your Art's base stat must be either Power or Knowledge. Make sure that your format "
                              "is: name, damage value, base stat, and effects (if any).")
        # Check if an Art with that name already exists and, if so, remove the existing Art before proceeding.
        art_to_edit = None
        art_modified = False
        for art in arts:
            if name.lower() == art.name.lower():
                art_to_edit = art
        if art_to_edit:
            caller.delete_art(art_to_edit)
            art_modified = True
        # Now check that the character does not already have the maximum number of Arts: 10.
        if len(arts) == 10:
            return caller.msg("Your character already has the maximum of 10 Arts. Art not added.")
        # Set the baseline AP cost for an art at 5.
        true_ap_change = -5
        if len(art_list) == 4:
            effects = art_list[3]
            # Split up the effects at the space bar.
            split_effects = effects.split()
            # Make sure the effects are in title case, except for EX.
            title_split_effects = []
            for effect in split_effects:
                if effect.lower() == "ex":
                    title_split_effects.append(effect.upper())
                else:
                    title_case_effect = effect.title()
                    title_split_effects.append(title_case_effect)
            # Now, for each effect in the split_effects list, confirm that it is in EFFECTS.
            # If so, modify the art's AP cost based on the data in EFFECTS.
            ex_move = False
            for art_effect in title_split_effects:
                effect_ok = False
                for real_effect in EFFECTS:
                    if art_effect.lower() == real_effect.name.lower():
                        effect_ok = True
                        true_ap_change += int(real_effect.ap)
                        if real_effect.name == "EX":
                            ex_move = True
                if not effect_ok:
                    return caller.msg("Error: at least one of your Effects is not a valid Effect.")
            # Confirm that any Support effect is coupled with the Heal effect
            for effect in title_split_effects:
                if effect in SUPPORT and "Heal" not in title_split_effects:
                    return caller.msg(f"Error: {effect} is a Support effect. All Support Arts must have the Heal Effect.")
                if effect in DEBUFFS and "Heal" in title_split_effects:
                    return caller.msg(f"Error: {effect} is a Debuff effect and is not compatible with the Heal Effect.")
            # Confirm that accuracy is above minimum before adding Art object.
            accuracy, error_string = accuracy_check(accuracy, ex_move)
            if error_string:
                return caller.msg(error_string)
            Arts.objects.create(
                name=name,
                ap=true_ap_change,
                dmg=damage_int,
                acc=accuracy,
                stat=base_stat,
                effects=' '.join(title_split_effects),
                )
        else:
            accuracy, error_string = accuracy_check(accuracy)
            if error_string:
                return caller.msg(error_string)
            Arts.objects.create(
                name=name,
                ap=true_ap_change,
                dmg=damage_int,
                acc=accuracy,
                stat=base_stat,
                effects=""
            )
        caller.arts.add(Arts.objects.latest("pk"))
        # Change the message to the player depending on if the Art was added or edited.
        if not art_modified:
            caller.msg("{0} has been added to your list of Arts.".format(name))
        else:
            caller.msg("{0} has been modified on your list of Arts.".format(name))


class CmdChargen(default_cmds.MuxCommand):
    """
        A character generation command used to set your five stats: Power,
        Knowledge, Parry, Barrier, and Speed. The total must be equal to
        your character's Stat Total. By default, this is 625, or 125 per stat.
        Think of 100 as "average," 150 as "good," and 200 as "exceptional."

        The current stat minimum is 50 and maximum is 210. Special dispensation
        is required for any stat lower or higher than this.

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
            return caller.msg("Your stats total {0}. Please ensure your total stat value is equal to {1}.".format(split_args_sum, stat_total))
        # Make sure that no stat is above 210 or below 50.
        for stat in split_args:
            if int(stat) > 210:
                return caller.msg("Please ensure that no stat is above the maximum of 210.")
            if int(stat) < 50:
                return caller.msg("Please ensure that no stat is below the minimum of 50.")
        # Set the stats accordingly.
        caller.db.power = int(split_args[0])
        caller.db.knowledge = int(split_args[1])
        caller.db.parry = int(split_args[2])
        caller.db.barrier = int(split_args[3])
        caller.db.speed = int(split_args[4])
        caller.msg("Your stats have been set. Confirm them with +sheet.")
