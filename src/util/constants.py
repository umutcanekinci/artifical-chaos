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

SCARAB_HP           = 40
SCARAB_SPEED        = 60
AGGRO_RADIUS         = 400  # drones notice the player/soldiers within this range
MELEE_RANGE         = 40
FIRE_RANGE          = 250
MELEE_DAMAGE        = 10
FIRE_DAMAGE         = 8
MELEE_COOLDOWN_MS   = 700
FIRE_COOLDOWN_MS    = 900

PLAYER_FIRE_RANGE       = 300
PLAYER_FIRE_DAMAGE      = 12
PLAYER_FIRE_COOLDOWN_MS = 300

SOLDIER_FIRE_RANGE       = 250
SOLDIER_FIRE_DAMAGE      = 10
SOLDIER_FIRE_COOLDOWN_MS = 500