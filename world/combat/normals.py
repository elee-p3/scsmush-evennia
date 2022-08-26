from world.combat.attacks import Attack
quick_attack = Attack("Quick Attack", 20, 10, 90, "Power")
medium_attack = Attack("Medium Attack", 20, 30, 70, "Power")
strong_attack = Attack("Strong Attack", 20, 50, 50, "Power")
heavy_attack = Attack("Heavy Attack", 20, 70, 30, "Power")
quick_art = Attack("Quick Art", 20, 10, 90, "Knowledge")
medium_art = Attack("Medium Art", 20, 30, 70, "Knowledge")
strong_art = Attack("Strong Art", 20, 50, 50, "Knowledge")
heavy_art = Attack("Heavy Art", 20, 70, 30, "Knowledge")
NORMALS = [quick_attack, medium_attack, strong_attack, heavy_attack, quick_art, medium_art,strong_art, heavy_art]