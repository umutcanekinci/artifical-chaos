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

# Startup splash (pygame_core.SplashScreen): fade-in then hold, per image --
# same values as chokepoint/highrise/hunted/standoff, which all show the
# same pygame_logo.png this way.
SPLASH_FADE_MS = 1500
SPLASH_HOLD_MS = 1000

# In-game controls tutorial (gameplay/tutorial.py) -- a linear "press this
# key" HUD overlay shown at the start of a run (MOVE -> FIRE -> SQUAD
# STANCE), not persisted across runs (no save/load exists yet, see
# CLAUDE.md's Persistence note) and gone for good the instant every step's
# been completed once. Icons are Kenney's CC0 input-prompts pack (see
# ASSETS.md), assets/images/input_prompts/ -- only the "Default" keyboard/
# mouse style is bundled (no gamepad platforms, no Double/Vector/Fonts
# variants), since this game has no gamepad support to prompt for.
TUTORIAL_ICON_SIZE = 48
TUTORIAL_ICON_GAP = 0
# Wider gap between whole key-groups (and the "OR" connector between them)
# than between icons within one group -- MOVE shows a WASD cluster and an
# arrow-key cluster side by side, connected by "OR", since either works.
TUTORIAL_GROUP_GAP = 16
TUTORIAL_FONT_SIZE = 22
TUTORIAL_PANEL_PADDING = 12
TUTORIAL_PANEL_ALPHA = 170
TUTORIAL_TOP_MARGIN = 24

# Flag capture (gameplay/flag.py) -- the v1 win condition ("defeat all
# drones") has been replaced by this richer one: hold every flag until it's
# fully captured. A flag can only progress while the player or an in-army
# soldier is within FLAG_CAPTURE_RADIUS *and* no drone is within the wider
# FLAG_CONTEST_RADIUS -- since every flag spawns with a drone standing
# right on it (see Map.spawn_objects), clearing that guardian first is a
# natural prerequisite, not a separate rule. First-pass numbers, not tuned.
#
# FLAG_CAPTURE_ELLIPSE_RX/RY (the radial capture-progress fill drawn behind
# the flag, gameplay/ui.py's draw_radial_progress) are defined first and
# FLAG_CAPTURE_RADIUS reuses the smaller of the two -- they used to be
# independently-tuned numbers, and the gameplay radius being bigger than
# the visual fill meant you could stand visibly outside the ring and still
# be capturing it, which read as a bug ("capture area is a bit big"). Not
# an ellipse check (find_nearest is circular-only, see gameplay/combat.py)
# -- using the smaller axis (RY) keeps the capture circle fully inside the
# ellipse instead of poking out its narrow (vertical) sides. The ellipse
# itself isn't picked freehand: assets/images/ui/objective-pulse.png's
# largest actually-used frame (index 5 of the 6 Flag.__init__ loads) has a
# get_bounding_rect() of 60x41 source px -- an ellipse, not a circle -- so
# the fill uses that same aspect ratio and max size (halved for radius, x3
# for SCALE_FACTOR) rather than an arbitrary circle that wouldn't match the
# pulse ring it sits behind.
FLAG_CAPTURE_ELLIPSE_RX = 60 * SCALE_FACTOR // 2
FLAG_CAPTURE_ELLIPSE_RY = 41 * SCALE_FACTOR // 2
FLAG_CAPTURE_FILL_ALPHA = 180  # out of 255 -- a bit see-through, not solid

FLAG_CAPTURE_RADIUS = FLAG_CAPTURE_ELLIPSE_RY
FLAG_CONTEST_RADIUS = 150
FLAG_CAPTURE_RATE   = 35  # % per second while held and uncontested (was 20 -- felt slow)
FLAG_DECAY_RATE     = 15  # % per second lost while contested

# Flag spawner (Flag._spawn_drone()) -- an uncaptured flag keeps spawning
# reinforcement drones near itself on this cooldown, picked at random from
# every wired-up DRONE_CLASSES type, capped at FLAG_SPAWN_MAX_CONCURRENT
# alive from that flag at once. Added because the original single guardian
# (Map.spawn_objects()) could die quickly and leave nothing contesting the
# flag at all -- winning was too easy partly because there just weren't
# enough enemies around. Bounded and self-terminating (stops the instant
# the flag is captured), not an idle/endless-survival spawner: the map
# still has exactly 9 flags, so this adds sustained pressure at each one
# rather than an unbounded global wave system. First-pass numbers, not tuned.
FLAG_SPAWN_COOLDOWN_MS      = 8000
FLAG_SPAWN_MAX_CONCURRENT   = 3
FLAG_SPAWN_RADIUS           = 80  # random offset from the flag's own position

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

# Visible/collidable rock obstacles (gameplay/map.py's RockObstacle) --
# unlike every wall so far (invisible tile colliders, see Obstacle),
# these use a real sprite from obstacles-and-objects.png, so the map has
# *some* obstacles you can actually see coming, not just invisible
# collision. Frame ids 64-68 are five standalone boulder variants on the
# sheet's own 16px grid -- confirmed by get_bounding_rect() on each 16x16
# slice (each fills its own cell edge-to-edge, no bleed into neighbors) and
# by rendering them individually; an initial guess at row 2 (ids 32-36)
# turned out to be tiny unrelated shard/crystal props once actually
# checked the same way, not boulders -- the low-res labeled-grid thumbnail
# used to first survey this sheet was too coarse to tell them apart by eye.
# The sheet's car sprites visibly bleed past their grid cells when sliced
# the same way, so they're not used here without confirming their real
# frame size first.
ROCK_OBSTACLE_SIZE = 16
ROCK_OBSTACLE_FRAME_IDS = [64, 65, 66, 67, 68]
ROCK_OBSTACLE_COUNT = 18
ROCK_OBSTACLE_SEED = 11

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
#
# `muzzle_effect` picks which ranged-hit flash Drone.attack() spawns:
# "gunpowder" (MuzzleFlash, muzzle-flashes.png) for the insectoid/mechanical
# types, "laser" (LaserFlash, laser-flash.png) for Hornet/Wasp specifically,
# since GDD.md describes them as energy-based rather than gunpowder-firing.
#
# `stand_off_range` is 0 for every type that's fine holding position at
# fire_range (Drone.engage() branches on it being > 0 to back away instead
# of holding still once a target closes inside it -- "by construction",
# same idiom as melee_range: 0/splash_radius: 0/support_cooldown_ms: 0
# elsewhere). Only Hornet has one: ranged-only (melee_range: 0) but used to
# just hold ground like every other drone once a target got close, instead
# of actually keeping the stand-off distance its GDD role implies.
# First balance pass (2026-07): every hp below was raised from its original
# value -- a full squad (player + several soldiers, each independently
# capable of ~20-40 dps, see SOLDIER_CLASSES/PLAYER_FIRE_* below) converging
# on one drone could otherwise melt even the toughest type in under a
# second, which both made winning trivial and meant Centipede specifically
# died before its segmented body (gameplay/robot.py's CentipedeSegment
# chain) ever visibly moved -- it only stretches out while the head is
# still walking toward a target, and freezes the instant it's close enough
# to fight, so a fight that's over almost immediately never shows it at
# all. Still first-pass, not fully tuned -- a starting point for further
# playtesting, not a final answer.
DRONE_TYPES = {
    "Scarab": {
        "hp": 70, "speed": 60,
        "melee_range": 40, "fire_range": 250,
        "melee_damage": 10, "fire_damage": 8,
        "melee_cooldown_ms": 700, "fire_cooldown_ms": 900,
        "sprite_size": SPRITE_SIZE,
        "clip_rows": {"idle": 0, "walking": 1, "fire": 2, "melee": 3},
        "destroyed_row": 4,
        "muzzle_effect": "gunpowder",
        "stand_off_range": 0,
    },
    "Spider": {
        # Fast flanker that prefers melee (GDD role): high speed closes
        # distance fast, and a short fire_range means it rarely bothers
        # shooting from afar instead of just closing in to melee.
        "hp": 55, "speed": 110,
        "melee_range": 50, "fire_range": 90,
        "melee_damage": 14, "fire_damage": 5,
        "melee_cooldown_ms": 500, "fire_cooldown_ms": 1000,
        "sprite_size": SPRITE_SIZE,
        "clip_rows": {"idle": 0, "walking": 1, "fire": 2, "melee": 3},
        "destroyed_row": 4,
        "muzzle_effect": "gunpowder",
        "stand_off_range": 0,
    },
    "Hornet": {
        # Flying, ranged-only (GDD role): melee_range 0 means the melee
        # branch in Drone.engage() never triggers (distance is never <= 0).
        # stand_off_range 150 (half of fire_range) makes it back away while
        # still firing once a target closes inside that, instead of just
        # holding ground like every other drone -- an actual kiting flanker.
        "hp": 70, "speed": 75,
        "melee_range": 0, "fire_range": 300,
        "melee_damage": 0, "fire_damage": 7,
        "melee_cooldown_ms": 900, "fire_cooldown_ms": 850,
        "sprite_size": 24,
        "clip_rows": {"idle": 0, "walking": 0, "fire": 1, "melee": 1},
        "destroyed_row": None,
        "muzzle_effect": "laser",
        "stand_off_range": 150,
    },
    "Wasp": {
        # Only a single hover animation exists on the sheet (no separate
        # firing pose) -- every clip_rows entry points at row 0, so it just
        # looks the same in every status. Fast, fragile skirmisher.
        "hp": 25, "speed": 140,
        "melee_range": 0, "fire_range": 200,
        "melee_damage": 0, "fire_damage": 4,
        "melee_cooldown_ms": 500, "fire_cooldown_ms": 500,
        "sprite_size": SPRITE_SIZE,
        "clip_rows": {"idle": 0, "walking": 0, "fire": 0, "melee": 0},
        "destroyed_row": None,
        "muzzle_effect": "laser",
        "stand_off_range": 0,
    },
    "Centipede": {
        # Heavy, slow siege unit (GDD role) -- the one drone type with a
        # genuinely segmented body (gameplay/robot.py's CentipedeSegment),
        # so hp/speed lean tankier/slower than everything else here. Stats
        # below are for the head only; segments have no hp/combat of their
        # own. Sheet layout confirmed by rendering Centipede.png with a
        # 16px grid overlay (128x288 = 8 cols x 18 rows @16px, same
        # approach as Hornet/Wasp): rows 0-3 are an armored head in 4
        # distinct states, picked in row order for idle/walking/fire/melee
        # since nothing in the asset pack documents which is "meant" to be
        # which; rows 8-16 are plain round body-segment frames with no
        # head armor (see CENTIPEDE_SEGMENT_ROWS) -- no destroyed frame
        # either, so it's removed immediately on death like Hornet/Wasp.
        # hp is deliberately far above every other type (see the balance-
        # pass note above DRONE_TYPES): a mini-boss-weight pool so the fight
        # actually lasts long enough for the segment chain to be visibly
        # trailing/moving before it dies, not just a bigger number for its
        # own sake.
        "hp": 400, "speed": 45,
        "melee_range": 45, "fire_range": 200,
        "melee_damage": 18, "fire_damage": 6,
        "melee_cooldown_ms": 800, "fire_cooldown_ms": 1000,
        "sprite_size": SPRITE_SIZE,
        "clip_rows": {"idle": 0, "walking": 1, "fire": 2, "melee": 3},
        "destroyed_row": None,
        "muzzle_effect": "gunpowder",
        "stand_off_range": 0,
    },
}

# Centipede's trailing body (gameplay/robot.py) -- each CentipedeSegment
# holds CENTIPEDE_SEGMENT_GAP behind the one in front of it (a rigid
# chain-link constraint solved fresh every frame, not a spring, so segments
# hold a fixed distance instead of oscillating or drifting). One row per
# segment from Centipede.png's plain body-segment block (rows 8-16) so
# segments along the body aren't all identical; only 5 of those 9 rows are
# used, picked arbitrarily -- first-pass, not tuned for a "correct" order.
CENTIPEDE_SEGMENT_ROWS = [8, 9, 10, 11, 12]
CENTIPEDE_SEGMENT_GAP  = 36

PLAYER_FIRE_RANGE       = 300
PLAYER_FIRE_DAMAGE      = 12
PLAYER_FIRE_COOLDOWN_MS = 300

# Rank-up bonuses (Player.rank_up()) -- triggered by Flag.update() the
# instant a flag's progress hits 100% (gameplay/flag.py), so rank tracks
# flags captured, not soldiers recruited or drones killed. Each rank-up
# picks RANK_UP_STATS_FEW_RANKS distinct stats at random (out of the four
# below) to buff by one step, rather than always buffing all four or
# always just one -- with only a handful of flags on the map (this map has
# 9, at or under MAX_RANK), a run might otherwise finish without ever
# touching one of the four stats; RANK_UP_STATS_MANY_RANKS applies once a
# map has enough flags/ranks that every stat will naturally come up
# several times anyway. First-pass bonus amounts, not balanced.
RANK_UP_HP_BONUS            = 10  # added to max_hp (and current hp)
RANK_UP_SPEED_BONUS         = 5   # added to ms
RANK_UP_FIRE_RATE_BONUS_MS  = 20  # subtracted from fire_cooldown_ms
RANK_UP_FIRE_RATE_MIN_MS    = 100  # floor so repeated picks can't reach 0/negative
RANK_UP_DAMAGE_BONUS        = 2   # added to fire_damage
RANK_UP_STATS_FEW_RANKS     = 2
RANK_UP_STATS_MANY_RANKS    = 1
RANK_UP_MANY_RANKS_THRESHOLD = MAX_RANK  # total flags at/above which only RANK_UP_STATS_MANY_RANKS applies

# Floating rank-up feedback (gameplay/effects.py's FloatingText) -- a short
# colored label ("+HP", "+DMG", ...) that rises above the Squad Leader and
# fades out. Colors are picked to read at a glance, not tied to any other
# palette in the game (HP reuses HP_BAR_HEALTHY's green since that
# association already exists via the health bar).
FLOATING_TEXT_FONT_SIZE     = 22
FLOATING_TEXT_RISE_DISTANCE = 60
FLOATING_TEXT_DURATION_MS   = 900
FLOATING_TEXT_X_SPACING     = 26  # horizontal offset between simultaneous picks so they don't overlap
RANK_UP_STAT_LABELS = {
    "hp": "+HP",
    "speed": "+SPD",
    "fire_rate": "+RATE",
    "damage": "+DMG",
}
RANK_UP_STAT_COLORS = {
    "hp": (80, 220, 80),     # green, matches HP_BAR_HEALTHY
    "speed": (90, 170, 240),  # blue
    "fire_rate": (240, 210, 70),  # yellow
    "damage": (230, 80, 80),  # red
}

# Soldier.engage()'s fire branch only actually calls attack() while the
# player's own velocity is under this -- soldiers still find a target,
# hold position, and aim (status stays "fire") while the player is moving,
# they just don't land the hit. Deliberately not 0 (residual friction
# creep would almost never read as truly stationary otherwise). This is
# the second balance-pass mechanic (see GDD.md): makes "stop to let your
# squad actually fight" vs. "keep moving and leave them mid-aim" a real
# moment-to-moment decision, without touching who they target -- the
# no-individual-micromanagement pillar stays intact, this only gates
# *whether* the already-autonomous targeting is allowed to connect.
SQUAD_ATTACK_MAX_PLAYER_SPEED = 5

# Soldier.walk()'s original hard-coded "only move once farther than 100px
# from the player" distance, named so the guard-stance constants below can
# reference it instead of repeating the number. This is the "engage" stance's
# hold distance -- Player.squad_stance defaults to "engage" (see
# Player.toggle_squad_stance(), Game.handle_event(), TAB key), so behavior is
# unchanged from before the stance toggle existed unless the player switches.
SOLDIER_HOLD_DISTANCE = 100

# The third and final piece of the second balance/mechanics pass (see
# GDD.md): a Tab-toggle between "engage" (default, unchanged behavior above)
# and "guard" -- a tighter, protect-the-commander formation for moments where
# spreading the squad out to chase every drone in range is the wrong call.
# In "guard": Soldier.walk() holds a much shorter distance from the player
# (stays in a tight escort formation instead of ranging out to ~100px), and
# engage() won't bother fighting a drone more than SQUAD_GUARD_ENGAGE_RADIUS
# away from the player even if it's well within the soldier's own fire_range
# -- both numbers only change *where* the already-autonomous nearest-target
# selection is allowed to look/wander, never *which* target it picks, so the
# no-individual-micromanagement pillar stays intact same as the stationary-
# fire gate above.
SQUAD_GUARD_HOLD_DISTANCE = 40
SQUAD_GUARD_ENGAGE_RADIUS = 150
SQUAD_STANCE_LABELS = {"engage": "ENGAGE", "guard": "GUARD"}
SQUAD_STANCE_COLORS = {
    "engage": (230, 80, 80),   # red, matches RANK_UP_STAT_COLORS["damage"]
    "guard": (80, 220, 80),    # green, matches RANK_UP_STAT_COLORS["hp"]
}

# Player.draw_squad_stance() -- a persistent bottom-left HUD label (unlike
# the one-shot FloatingText toggle_squad_stance() pops, this never fades,
# so the current stance stays visible at a glance instead of only being
# shown for an instant right when it changes).
SQUAD_STANCE_HUD_FONT_SIZE = 28
SQUAD_STANCE_HUD_MARGIN = 20

# Per-soldier-class stats. All six classes are now wired up.
#
# Every "speed" is deliberately > the player's own 100 (see Player.ms in
# player.py): Soldier.walk() only moves once farther than 100px from the
# player, so a soldier that falls behind while the player keeps moving
# needs to be faster to ever close that gap again -- at speed <= 100 it
# can never catch up once behind, no matter how long you wait. Relative
# ordering (AntiTank slowest, matching its "slow, tanky" GDD role) is kept,
# just shifted above the player's speed instead of below it.
#
# "splash_radius" is 0 for every single-target class (Soldier.attack()
# branches on it being > 0 to run Grenadier's AoE path instead -- "by
# construction", the same idiom DRONE_TYPES' Hornet uses for melee_range: 0,
# rather than a special-cased "is this a Grenadier" check). Grenadier's own
# "fire_damage" is per-target, not a total -- a cluster of drones caught in
# one throw can add up to well more than a single-target class's hit, which
# is the intended tradeoff for its slow fire_cooldown_ms.
#
# "support_cooldown_ms" is 0 for every fighting class, same "by
# construction" idiom as splash_radius above: nonzero only for
# RadioOperator-Class, whose engage() branches on it to skip combat
# entirely and periodically call in a reinforcement soldier instead (see
# Soldier.call_reinforcement()) -- the GDD's own suggested option for its
# support ability, picked over "reveal the map" (this game already has no
# fog of war, nothing to reveal) or a stat-boosting aura (would need
# tracking each buffed soldier's un-boosted base stats to undo the buff
# once out of range, real complexity for a first pass).
SOLDIER_CLASSES = {
    "Assault-Class": {
        "speed": 120, "fire_range": 250, "fire_damage": 10, "fire_cooldown_ms": 500,
        "splash_radius": 0, "support_cooldown_ms": 0,
    },
    "Sniper-Class": {
        "speed": 110, "fire_range": 450, "fire_damage": 25, "fire_cooldown_ms": 1200,
        "splash_radius": 0, "support_cooldown_ms": 0,
    },
    "MachineGunner-Class": {
        "speed": 110, "fire_range": 180, "fire_damage": 4, "fire_cooldown_ms": 150,
        "splash_radius": 0, "support_cooldown_ms": 0,
    },
    "AntiTank-Class": {
        "speed": 105, "fire_range": 200, "fire_damage": 35, "fire_cooldown_ms": 1500,
        "splash_radius": 0, "support_cooldown_ms": 0,
    },
    "Grenadier-Class": {
        "speed": 115, "fire_range": 220, "fire_damage": 15, "fire_cooldown_ms": 1400,
        "splash_radius": 90, "support_cooldown_ms": 0,
    },
    "RadioOperator-Class": {
        "speed": 110, "fire_range": 0, "fire_damage": 0, "fire_cooldown_ms": 0,
        "splash_radius": 0, "support_cooldown_ms": 15000,
    },
}

# Reinforcement soldiers called in by RadioOperator-Class (Soldier.
# call_reinforcement()) are picked from the other combat-capable classes
# (support_cooldown_ms == 0), spawned at a small random offset from the
# caller so they don't land exactly on top of it, and immediately added to
# the army like any recruited soldier. Reuses FloatingText (see rank-up
# above) for the same at-a-glance feedback rank-ups get.
RADIO_OPERATOR_REINFORCEMENT_OFFSET = 40
RADIO_OPERATOR_CALL_LABEL = "+SQUAD"
RADIO_OPERATOR_CALL_COLOR = (90, 170, 240)  # matches RANK_UP_STAT_COLORS["speed"]

# Effects (gameplay/effects.py) -- purely cosmetic one-shot animations
# spawned by attack()/die() call sites; gameplay/combat.py itself stays
# side-effect-free so combat logic is still testable without a real
# Animator/renderer. Frame counts/sizes were confirmed by rendering each
# sheet with a grid overlay and inspecting it (no info.txt for these,
# unlike the robot/soldier sheets). fps values are first-pass, not tuned.
MUZZLE_FLASH_FPS = 30    # assets/images/effects/muzzle-flashes.png, 4 frames @ 8px
LASER_FLASH_FPS  = 30    # assets/images/effects/laser-flash.png, 3 frames @ 16px -- Hornet/Wasp only
HIT_SPARK_FPS    = 24    # assets/images/effects/hit-sparks.png, 6 frames @ 8px -- drone hits
HIT_SPATTER_FPS  = 24    # assets/images/effects/hit-spatters.png, 6 frames @ 8px -- player/soldier hits
EXPLOSION_FPS    = 20    # assets/images/effects/small-explosion.png, 9 frames @ 24px -- drone destruction
BIG_EXPLOSION_FPS = 18   # assets/images/effects/big-explosion.png, 11 frames @ 32px -- Grenadier splash impact,
                         # deliberately distinct from Explosion (drone death) so a thrown grenade landing
                         # reads differently from a drone dying
SMOKE_FPS = 10           # assets/images/effects/smoke.png, 8 frames @ 8px -- slower than EXPLOSION_FPS/
                         # BIG_EXPLOSION_FPS on purpose, so it visibly outlasts either fireball (see Smoke)

# Tracer (gameplay/effects.py) is a visual-only "bullet" that flies from
# attacker to target -- damage is already applied by the time it spawns
# (hitscan resolves instantly, see gameplay/combat.py), so its only job is
# to read on-screen; it never gates anything.
TRACER_SIZE        = 8   # assets/images/projectiles/bullets+plasma.png frame 0
TRACER_DURATION_MS = 90

# Grenade (gameplay/effects.py) is Tracer's lobbed counterpart for
# Grenadier-Class's splash attack -- also visual-only (splash damage is
# applied instantly at throw time, see Soldier.attack()'s splash branch),
# but spins through its own sheet while arcing instead of holding one frame,
# and takes longer to cross the screen to read as thrown, not fired.
GRENADE_SIZE        = 8   # assets/images/projectiles/Grenade.png, 8 frames @ 8px
GRENADE_SPIN_FPS    = 16
GRENADE_FLIGHT_MS   = 400

# BulletImpact (gameplay/effects.py) -- a static wall-impact decal, spawned
# only from Player.shoot()'s "held the button, no drone in range" branch: a
# cosmetic-only raycast (gameplay/combat.py's raycast(), never gates real
# hit resolution) checks whether the shot would have hit a wall, and if so
# a random decal frame is dropped there. Static (no animation, unlike every
# other effect here), so it just holds one of bullet-impacts.png's 10
# frames for BULLET_IMPACT_DURATION_MS instead of playing a clip -- fades
# out eventually rather than being truly permanent so it can't accumulate
# without bound over a long play session.
BULLET_IMPACT_SIZE         = 8   # assets/images/effects/bullet-impacts.png, 10 frames @ 8px, single row
BULLET_IMPACT_FRAME_COUNT  = 10
BULLET_IMPACT_DURATION_MS  = 10000