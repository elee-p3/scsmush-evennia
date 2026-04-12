from world.arts.models import Art
from world.combat.effects import EFFECTS, SUPPORT, DEBUFFS, DEBUFFS_HEXES


def accuracy_check(accuracy, ex_move=False):
    error_msg = ""
    if ex_move:
        accuracy = accuracy + 2
    if accuracy <= 0:
        error_msg = "Error: your damage value must be an integer between 1 and 11 (or 13 for EX moves). Make sure " \
                 "that your format is: name, damage value, base stat, and effects (if any)."
    return accuracy, error_msg


def create_or_edit_art(caller, name, damage, base_stat, effects, *, bypass_cap=False):
    """Returns either Art, '', art_modified bool on success or None, error_msg, False on failure."""
    arts = Art.objects.filter(characters=caller)
    error_msg = ""
    art_modified = False

    # Base accuracy for Arts will be 12 - damage_int, increased by 2 for EX moves after effects are checked.
    accuracy = 12 - damage
    # Checking that the base stat is either Power or Knowledge.
    if base_stat == "power":
        base_stat = "Power"
    elif base_stat == "knowledge":
        base_stat = "Knowledge"
    else:
        return None, "Error: your Art's base stat must be either Power or Knowledge. Make sure that your format is: " \
                     "name, damage value, base stat, and effects (if any).", art_modified

    # Check if an Art with that name already exists and, if so, remove the existing Art before proceeding.
    art_to_edit = None

    for art in arts:
        if name.lower() == art.name.lower():
            art_to_edit = art
    if art_to_edit:
        caller.delete_art(art_to_edit)
        art_modified = True

    # Now check that the character does not already have the maximum number of Arts: 10.
    if not bypass_cap and len(arts) == 10:
        return None, "Your character already has the maximum of 10 Arts. Art not added.", art_modified

    # Set the baseline AP cost for an art at 5.
    true_ap_change = -5
    if effects:
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
                return None, "Error: at least one of your Effects is not a valid Effect.", art_modified

        # Confirm that any Support effect is coupled with the Heal effect
        for effect in title_split_effects:
            if effect in SUPPORT and "Heal" not in title_split_effects:
                return None, f"Error: {effect} is a Support effect. All Support Arts must have the Heal Effect.", art_modified
            if effect in DEBUFFS and "Heal" in title_split_effects:
                return None, f"Error: {effect} is a Debuff effect and is not compatible with the Heal Effect.", art_modified

        # Confirm that accuracy is above minimum before adding Art object.
        accuracy, error_msg = accuracy_check(accuracy, ex_move)
        if error_msg:
            return None, error_msg, art_modified

        Art.objects.create(
            name=name,
            ap=true_ap_change,
            dmg=damage,
            acc=accuracy,
            stat=base_stat,
            effects=' '.join(title_split_effects),
        )

    else:
        accuracy, error_msg = accuracy_check(accuracy)
        if error_msg:
            return None, error_msg, art_modified

        Art.objects.create(
            name=name,
            ap=true_ap_change,
            dmg=damage,
            acc=accuracy,
            stat=base_stat,
            effects=""
        )

    caller.art.add(Art.objects.latest("pk"))

    return art, error_msg, art_modified
