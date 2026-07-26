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

# Minimum |target.x - self.x| before an attacker flips its sprite facing.
# Without this, an attacker crossing to the other side of its target has
# delta.x hover right around 0, flickering sign every frame from ordinary
# movement noise and flipping the mirrored sprite each time -- visible as
# jitter. Only matters while actively re-deriving facing from a target
# position each frame (Drone.engage(), Soldier.engage()); Player.walk()'s
# facing comes from discrete key state instead, so it isn't affected.
FACING_DEADZONE = 4

# Per-drone-type stats + sheet layout. `clip_rows` maps a logical animation
# name to its sheet row -- pointing two names at the same row (e.g. Hornet's
# "idle"/"walking" both at row 0) is how a type with fewer real animations
# than Scarab/Spider still works with the same Drone code, no branching
# needed. `destroyed_row` is None for types without a destroyed frame
# (Hornet, Wasp) -- those are removed immediately on death instead of
# holding a destroyed pose, see Drone.die(). `sprite_size` is the source
# frame size in pixels (most are SPRITE_SIZE/16px; Hornet's sheet uses 24px
# frames, confirmed by inspecting assets/images/robots/Hornet.png directly
# since Robot animation info.txt doesn't document it). Centipede is still
# not wired up -- its sheet looks like a modular/segmented body (many more
# rows than a simple animation grid), a bigger job than a stat block, see
# GDD.md's Enemies section.
DRONE_TYPES = {
    "Scarab": {
        "hp": 40, "speed": 60,
        "melee_range": 40, "fire_range": 250,
        "melee_damage": 10, "fire_damage": 8,
        "melee_cooldown_ms": 700, "fire_cooldown_ms": 900,
        "sprite_size": SPRITE_SIZE,
        "clip_rows": {"idle": 0, "walking": 1, "fire": 2, "melee": 3},
        "destroyed_row": 4,
    },
    "Spider": {
        # Fast flanker that prefers melee (GDD role): high speed closes
        # distance fast, and a short fire_range means it rarely bothers
        # shooting from afar instead of just closing in to melee.
        "hp": 30, "speed": 110,
        "melee_range": 50, "fire_range": 90,
        "melee_damage": 14, "fire_damage": 5,
        "melee_cooldown_ms": 500, "fire_cooldown_ms": 1000,
        "sprite_size": SPRITE_SIZE,
        "clip_rows": {"idle": 0, "walking": 1, "fire": 2, "melee": 3},
        "destroyed_row": 4,
    },
    "Hornet": {
        # Flying, ranged-only (GDD role): melee_range 0 means the melee
        # branch in Drone.engage() never triggers (distance is never <= 0),
        # so it always either chases or fires -- it never actually keeps a
        # deliberate stand-off distance, that's a further-out polish item.
        "hp": 45, "speed": 75,
        "melee_range": 0, "fire_range": 300,
        "melee_damage": 0, "fire_damage": 7,
        "melee_cooldown_ms": 900, "fire_cooldown_ms": 850,
        "sprite_size": 24,
        "clip_rows": {"idle": 0, "walking": 0, "fire": 1, "melee": 1},
        "destroyed_row": None,
    },
    "Wasp": {
        # Only a single hover animation exists on the sheet (no separate
        # firing pose) -- every clip_rows entry points at row 0, so it just
        # looks the same in every status. Fast, fragile skirmisher.
        "hp": 18, "speed": 140,
        "melee_range": 0, "fire_range": 200,
        "melee_damage": 0, "fire_damage": 4,
        "melee_cooldown_ms": 500, "fire_cooldown_ms": 500,
        "sprite_size": SPRITE_SIZE,
        "clip_rows": {"idle": 0, "walking": 0, "fire": 0, "melee": 0},
        "destroyed_row": None,
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

# Effects (gameplay/effects.py) -- purely cosmetic one-shot animations
# spawned by attack()/die() call sites; gameplay/combat.py itself stays
# side-effect-free so combat logic is still testable without a real
# Animator/renderer. Frame counts/sizes were confirmed by rendering each
# sheet with a grid overlay and inspecting it (no info.txt for these,
# unlike the robot/soldier sheets). fps values are first-pass, not tuned.
MUZZLE_FLASH_FPS = 30    # assets/Effects/muzzle-flashes.png, 4 frames @ 8px
HIT_SPARK_FPS    = 24    # assets/Effects/hit-sparks.png, 6 frames @ 8px -- drone hits
HIT_SPATTER_FPS  = 24    # assets/Effects/hit-spatters.png, 6 frames @ 8px -- player/soldier hits
EXPLOSION_FPS    = 20    # assets/Effects/small-explosion.png, 9 frames @ 24px -- drone destruction

# Tracer (gameplay/effects.py) is a visual-only "bullet" that flies from
# attacker to target -- damage is already applied by the time it spawns
# (hitscan resolves instantly, see gameplay/combat.py), so its only job is
# to read on-screen; it never gates anything.
TRACER_SIZE        = 8   # assets/Projectiles/bullets+plasma.png frame 0
TRACER_DURATION_MS = 90