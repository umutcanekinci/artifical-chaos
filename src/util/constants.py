from pygame import Rect

FPS = 60
SIZE = (1920, 1080)  # fixed render resolution; Application upscales it (SCALED) to the display
SPRITE_SIZE = 16
FLAG_SIZE = 64
SCALE_FACTOR = 3
FOOTPRINT_DURATION = 300
DOT_DURATION = 300
AVOID_RADIUS = 50
FRICTION = 0.1
RANK_SIZE = 24
MAX_RANK = 15

# Combat -- ranges/damage are first-pass numbers, not balanced yet (see GDD.md).
# "Hitscan" throughout this codebase means an instant nearest-target-in-range
# check (gameplay/combat.py's find_nearest), not a directional raycast.
DESTROYED_DURATION_MS = 600  # how long a drone's destroyed frame holds before removal
AGGRO_RADIUS = 400  # drones notice the player/soldiers within this range, all types share it

# Per-drone-type stats. Only types with an idle/walk/fire/melee/destroyed
# sheet layout (Scarab, Spider) are wired up -- Hornet/Wasp/Centipede have
# undocumented or incompatible sheet layouts, see GDD.md's Enemies section.
DRONE_TYPES = {
    "Scarab": {
        "hp": 40, "speed": 60,
        "melee_range": 40, "fire_range": 250,
        "melee_damage": 10, "fire_damage": 8,
        "melee_cooldown_ms": 700, "fire_cooldown_ms": 900,
    },
    "Spider": {
        # Fast flanker that prefers melee (GDD role): high speed closes
        # distance fast, and a short fire_range means it rarely bothers
        # shooting from afar instead of just closing in to melee.
        "hp": 30, "speed": 110,
        "melee_range": 50, "fire_range": 90,
        "melee_damage": 14, "fire_damage": 5,
        "melee_cooldown_ms": 500, "fire_cooldown_ms": 1000,
    },
}

PLAYER_FIRE_RANGE       = 300
PLAYER_FIRE_DAMAGE      = 12
PLAYER_FIRE_COOLDOWN_MS = 300

# Per-soldier-class stats. Only classes that fit the existing single-target
# hitscan attack (find_nearest + cooldown + damage) are wired up here.
# Grenadier (arcing AoE) and RadioOperator (non-combat support ability) need
# mechanics this codebase doesn't have yet -- still asset-only, see GDD.md.
SOLDIER_CLASSES = {
    "Assault-Class": {
        "speed": 80, "fire_range": 250, "fire_damage": 10, "fire_cooldown_ms": 500,
    },
    "Sniper-Class": {
        "speed": 70, "fire_range": 450, "fire_damage": 25, "fire_cooldown_ms": 1200,
    },
    "MachineGunner-Class": {
        "speed": 70, "fire_range": 180, "fire_damage": 4, "fire_cooldown_ms": 150,
    },
    "AntiTank-Class": {
        "speed": 50, "fire_range": 200, "fire_damage": 35, "fire_cooldown_ms": 1500,
    },
}