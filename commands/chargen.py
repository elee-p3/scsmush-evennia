from evennia import default_cmds
from world.arts.models import Art
from world.arts.utilities import create_or_edit_art, concat_art_string
from world.combat.effects import EFFECTS, SUPPORT, DEBUFFS, DEBUFFS_HEXES
from world.combat.aspects import Aspect, ASPECTS, LinkedAspect
from world.aspects.models import LinkedAspect as LinkedAspectModel


class CmdSetArt(default_cmds.MuxCommand):
    """
        A character generation command that adds an Art to or
        edits an Art on your character's list of Arts. Specify
        its name, Damage, Base Stat (Power or Knowledge), and Effects.
        Damage must be an integer between 1 and 100.

        If +setart is called by itself, a series of specifying prompts will follow.
        Otherwise, name, Damage, Base Stat, and Effects should be separated by
        commas. In either case, different Effects should be separated by spaces.
        See "help effects" for a list of valid Effects.

        Characters may currently have a maximum of 10 Arts. To remove
        an Art, add the switch /del.

        Usage:
          +setart
          +setart <name of art>, <damage>, <base stat>, <effect1> <effect2>
          +setart/del <name of art>

    """

    key = "+setart"
    aliases = ["setart"]
    locks = "cmd:all()"


    def func(self):
        caller = self.caller
        args = self.args
        # TODO: https://github.com/elee-p3/scsmush-evennia/issues/38
        arts = Art.objects.filter(characters=caller)

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

        # If setart is called without args, prompt caller to concatenate the args one by one.
        if not args:
            args = yield from concat_art_string()

        # Split the args at the commas.
        art_list = args.split(", ")
        # Confirm correct number of commas via checking list length. 3 without effects, 4 with effects
        if len(art_list) < 3 or len(art_list) > 4:
            return caller.msg("Please comma-separate Art's name, damage value, base stat, and effects (if any).")

        name = art_list[0]
        damage = art_list[1]
        base_stat = art_list[2].lower()
        effects = []
        if len(art_list) == 4:
            effects = art_list[3]

        # Now that int type is confirmed, pass relevant information to utility function create_or_edit_art().
        art, error_msg, art_modified = create_or_edit_art(caller=caller, name=name, damage=damage, base_stat=base_stat, effects=effects)
        if error_msg:
            return caller.msg(error_msg)

        caller.art.add(Art.objects.latest("pk"))

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


class CmdGetAspect(default_cmds.MuxCommand):
    """
        A character generation command to acquire a new Aspect from all available.
        Acquired Aspects must be equipped to affect the character who acquires them.
        A "custom name" may also be provided that will be displayed in Sheet or ListAspects as:
        "Custom Name (Aspect)", e.g., "Brooch of Clarity (Charm Resistance)".

        If you are generating an Extra Art, specify "Extra Art" as the aspect and you will be
        prompted separately to define the Art. The Aspect and the Art may have different names:
        for example, the custom name of an "Extra Art" aspect might be "Wand of Fireballs" while
        the Art itself could be called "Fireball".

        Syntax:
            +getaspect <aspect>
            +getaspect <aspect>=<custom name>
    """

    key = "+getaspect"
    aliases = ["getaspect"]
    locks = "cmd:all()"

    def func(self):
        caller = self.caller
        args = self.args
        aspect_obj = None
        aspect_name = ""
        aspect_cost = 0
        aspect_custom_name = ""

        if "del" in self.switches:
            # .remove() won't work in the case of multiple Extra Arts. .pop() by index number.
            aspect_i_to_rem = None
            for i in range(len(caller.db.aspects)):
                # For an Extra Art, compare the args to the custom name.
                aspect = caller.db.aspects[i]
                if aspect == "Extra Art":
                    if args.lower() == aspect.custom_name.lower():
                        aspect_i_to_rem = i
                        aspect_obj = caller.db.aspects[aspect_i_to_rem]
                elif args.lower() == aspect.name.lower():
                    aspect_i_to_rem = i
                    aspect_obj = caller.db.aspects[aspect_i_to_rem]
            if not aspect_i_to_rem:
                return caller.msg("Aspect not found. No Aspect has been deleted.")
            else:
                # Ensure that nothing removed from the aspects list can remain in the equipped_aspects list.
                if aspect_obj in caller.db.equipped_aspects:
                    # Aspects and equipped_aspects are discrete lists, because I'm bad at coding, so find new index.
                    if aspect_obj.name == "Extra Art":
                        for i in range(len(caller.db.equipped_aspects)):
                            equipped_aspect = caller.db.equipped_aspects[i]
                            if args.lower() == equipped_aspect.custom_name.lower():
                                caller.db.cp += aspect_obj.cost
                                caller.db.equipped_aspects.pop(i)
                    else:
                        caller.db.cp += aspect_obj.cost
                        caller.db.equipped_aspects.remove(aspect_obj)
                caller.db.aspects.pop(aspect_i_to_rem)
                # TODO: figure out why this check isn't working and it's always showing custom_name and name
                if aspect_obj.custom_name:
                    return caller.msg(f"{aspect_obj.custom_name} ({aspect_obj.name}) has been removed from your Aspects.")
                else:
                    return caller.msg(f"{aspect_obj.name} has been removed from your Aspects.")

        # Confirm that the Aspect being sought exists in aspects.ASPECTS or as valid Expertise/Resistance.
        if "=" in args:
            aspect_to_find, aspect_custom_name = args.split("=")[0].lower(), args.split("=")[1]
        else:
            aspect_to_find = args.lower()

        # Corner case for custom names that might resemble actual Aspects so, e.g., CmdEquip can safely use custom_name.
        if aspect_custom_name in ASPECTS:
            return caller.msg("Error: requested custom name is an existing Aspect name.")

        elif "expertise" in aspect_custom_name.lower() or "resistance" in aspect_custom_name.lower():
            return caller.msg("Error: please refrain from using keywords 'Expertise' or 'Resistance' in custom names.")

        elif "expertise" in aspect_to_find or "resistance" in aspect_to_find:
            debuff_to_find = aspect_to_find.split()[0]
            if debuff_to_find in DEBUFFS:
                # Aspect valid. Determine cost: 1 if Hex, 5 otherwise
                aspect_name = aspect_to_find.title()
                if debuff_to_find in DEBUFFS_HEXES:
                    aspect_cost = 1
                else:
                    aspect_cost = 5
                aspect_obj = Aspect(name=aspect_name, cost=aspect_cost, custom_name=aspect_custom_name)

        # Handle case in which CmdGetAspects, in getting Extra Art, must generate a new Art.
        elif aspect_to_find == "extra art":
            # There must be a custom name because there can be multiple Extra Arts.
            if not aspect_custom_name:
                caller.msg("Extra Arts, unlike other Aspects, must have a custom name. Please specify with +getaspect "
                           "Extra Art=<custom name>.")
            # Aspect name will always be "Extra Art"
            aspect_name = aspect_to_find.title()
            # Prompt the user to specify CP cost and stat value.
            linked_aspect_cost = yield("Please specify the desired CP cost of your 'Extra Art' Aspect. This determines"
                                       " the stat value associated with your Extra Art when the Aspect is equipped. "
                                       "Valid inputs are: 10, 20, 30, or 40.")
            valid_linked_aspect_costs = ["10", "20", "30", "40"]
            if linked_aspect_cost in valid_linked_aspect_costs:
                aspect_cost = int(linked_aspect_cost)
            else:
                return caller.msg("The specified CP cost for your Linked Aspect was invalid. Please try again and "
                                  "choose 10, 20, 30, or 40.")

            # Now create the Linked Art.
            caller.msg("Please now define your Extra Art.")
            linked_art_string = yield from concat_art_string()

            # Split the args at the commas.
            art_list = linked_art_string.split(", ")
            # Confirm correct number of commas via checking list length. 3 without effects, 4 with effects
            if len(art_list) < 3 or len(art_list) > 4:
                return caller.msg("Please comma-separate Art's name, damage value, base stat, and effects (if any).")

            art_name = art_list[0]
            damage = art_list[1]
            base_stat = art_list[2].lower()
            effects = []
            if len(art_list) == 4:
                effects = art_list[3]

            art, error_msg, _ = create_or_edit_art(caller=caller, name=art_name, damage=damage,
                                                              base_stat=base_stat, effects=effects, bypass_cap=True)
            if error_msg:
                return caller.msg(error_msg)

            # Create a new LinkedAspectModel entry (name is custom_name, not "Extra Art") and add to database.
            new_aspect_entry = LinkedAspectModel.objects.create(name=aspect_custom_name, cost=aspect_cost, linked_art=art)
            aspect_id = new_aspect_entry.id
            # Then link to character in the database...
            caller.LinkedAspect.add(LinkedAspectModel.objects.latest("pk"))
            # ...and derive LinkedAspect from new entry, to add to character.db.aspects at the end of the function.
            aspect_obj = LinkedAspect(aspect_id, name=aspect_name, cost=aspect_cost, custom_name=aspect_custom_name)

        else:
            for aspect in ASPECTS:
                if aspect == aspect_to_find:
                    # Due to __eq__ magic method, lower() should match valid Aspect name
                    aspect_obj = Aspect(name=aspect.name, cost=aspect.cost, custom_name=aspect_custom_name)

        if aspect_obj is None:
            return caller.msg("Error: Aspect not found. Please confirm spelling and try again.")

        # Check if the character already has this Aspect. Exception is LinkedAspects, as there can be multiple Extra Arts.
        if not isinstance(aspect_obj, LinkedAspect):
            for acquired_aspect in caller.db.aspects:
                if acquired_aspect.name == aspect_obj.name:
                    # I don't want to allow multiple instances of the same Aspect, but we can overwrite custom_name
                    if acquired_aspect.custom_name != aspect_obj.custom_name:
                        acquired_aspect.custom_name = aspect_obj.custom_name
                        return caller.msg(f"Overwriting {acquired_aspect.name} custom name to {aspect_obj.custom_name}.")
                    else:
                        return caller.msg("Error: you already have this Aspect.")

        # Add the Aspect object with appropriate name and cost. custom_name will be displayed in CmdSheet/CmdListAspects.
        caller.db.aspects.append(aspect_obj)
        caller.msg(f"{aspect_obj.name} successfully added to your Aspects. Equip it with +equip.")