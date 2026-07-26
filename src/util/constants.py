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

# Flag capture (gameplay/flag.py) -- the v1 win condition ("defeat all
# drones") has been replaced by this richer one: hold every flag until it's
# fully captured. A flag can only progress while the player or an in-army
# soldier is within FLAG_CAPTURE_RADIUS *and* no drone is within the wider
# FLAG_CONTEST_RADIUS -- since every flag spawns with a drone standing
# right on it (see Map.spawn_objects), clearing that guardian first is a
# natural prerequisite, not a separate rule. First-pass numbers, not tuned.
FLAG_CAPTURE_RADIUS = 100
FLAG_CONTEST_RADIUS = 150
FLAG_CAPTURE_RATE   = 20  # % per second while held and uncontested
FLAG_DECAY_RATE     = 15  # % per second lost while contested

# Radii of the radial capture-progress fill (gameplay/ui.py's
# draw_radial_progress), drawn behind the flag/pulse sprites and centered
# on the flag -- unrelated to FLAG_CAPTURE_RADIUS above (that's a gameplay
# range in world units around the flag; this is purely the visual size).
# Matched to the flag's own pulse animation rather than picked freehand:
# assets/images/ui/objective-pulse.png's largest actually-used frame (index
# 5 of the 6 Flag.__init__ loads) has a get_bounding_rect() of 60x41 source
# px -- an ellipse, not a circle -- so the capture fill uses that same
# aspect ratio and max size (halved for radius, x3 for SCALE_FACTOR) rather
# than an arbitrary circle that wouldn't match the pulse ring it sits behind.
FLAG_CAPTURE_ELLIPSE_RX = 60 * SCALE_FACTOR // 2
FLAG_CAPTURE_ELLIPSE_RY = 41 * SCALE_FACTOR // 2
FLAG_CAPTURE_FILL_ALPHA = 180  # out of 255 -- a bit see-through, not solid

# HP bar (gameplay/ui.py's draw_health_bar) -- shared by Player, Soldier,
# and Drone, drawn overhead. The player's own bar is always visible (HP is
# the one stat where "you'd have to be told to go check" is actually a
# problem, unlike rank); Soldier/Drone only draw theirs once they've taken
# damage, so a screen full of undamaged units doesn't turn into a wall of
# full bars. Color tiers, not a smooth gradient, for a glance-able "how
# worried should I be" signal. Anchored off rect.top (not rect.centery like
# Flag's capture bar) -- these are tightly-cropped character/creature
# sprites, not the flag's padded pulse-ring asset, so rect.top tracks the
# visible sprite edge closely enough to just use directly.
HP_BAR_WIDTH    = 40
HP_BAR_HEIGHT   = 6
HP_BAR_GAP      = 10  # world-space px between rect.top and the bar
HP_BAR_HEALTHY  = (80, 220, 80)   # >= 60% hp
HP_BAR_HURT     = (230, 180, 60)  # 30-60% hp
HP_BAR_CRITICAL = (220, 60, 60)   # < 30% hp

# Recruited-soldier marker (Soldier.draw_recruited_marker) -- a ring drawn
# under any Soldier with is_in_army=True, so it's visually obvious which
# soldiers actually joined the squad (recruiting only triggers within 50px,
# easy to walk past without noticing) vs. which are still standing there
# dormant. assets/images/ui/selection-circles.png is a 2-col x 5-row grid
# of 24x24 frames (row 0 blank/unused, then green/red/blue/orange, each
# with a small/large column) -- row 1 col 0 is the small green ring.
# RECRUITED_MARKER_FINAL_SIZE is the on-screen diameter -- scaled to this
# directly (not just by SCALE_FACTOR) since the raw 24px source frame reads
# too large next to a 48px (16px * SCALE_FACTOR) soldier sprite.
# RECRUITED_MARKER_Y_OFFSET nudges it down from rect.centery so it sits
# under the sprite's feet instead of at its geometric (torso-height) center.
RECRUITED_MARKER_ROW = 1
RECRUITED_MARKER_COL = 0
RECRUITED_MARKER_SOURCE_SIZE = 24
RECRUITED_MARKER_FINAL_SIZE = 40
RECRUITED_MARKER_Y_OFFSET = 14

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
MUZZLE_FLASH_FPS = 30    # assets/images/effects/muzzle-flashes.png, 4 frames @ 8px
HIT_SPARK_FPS    = 24    # assets/images/effects/hit-sparks.png, 6 frames @ 8px -- drone hits
HIT_SPATTER_FPS  = 24    # assets/images/effects/hit-spatters.png, 6 frames @ 8px -- player/soldier hits
EXPLOSION_FPS    = 20    # assets/images/effects/small-explosion.png, 9 frames @ 24px -- drone destruction

# Tracer (gameplay/effects.py) is a visual-only "bullet" that flies from
# attacker to target -- damage is already applied by the time it spawns
# (hitscan resolves instantly, see gameplay/combat.py), so its only job is
# to read on-screen; it never gates anything.
TRACER_SIZE        = 8   # assets/images/projectiles/bullets+plasma.png frame 0
TRACER_DURATION_MS = 90