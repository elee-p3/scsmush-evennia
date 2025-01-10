from world.combat.attacks import Attack
quick_attack = Attack("Quick Attack", 20, 1, 9, "Power")
medium_attack = Attack("Medium Attack", 20, 3, 7, "Power")
strong_attack = Attack("Strong Attack", 20, 5, 5, "Power")
heavy_attack = Attack("Heavy Attack", 20, 7, 3, "Power")
quick_art = Attack("Quick Art", 20, 1, 9, "Knowledge")
medium_art = Attack("Medium Art", 20, 3, 7, "Knowledge")
strong_art = Attack("Strong Art", 20, 5, 5, "Knowledge")
heavy_art = Attack("Heavy Art", 20, 7, 3, "Knowledge")
NORMALS = [quick_attack, medium_attack, strong_attack, heavy_attack, quick_art, medium_art,strong_art, heavy_art]