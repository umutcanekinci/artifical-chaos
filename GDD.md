# Artificial Chaos — Game Design Document

Living document. Update it whenever a design decision is made so it doesn't
get lost between sessions again. Anything marked **[OPEN]** is an unresolved
question — pick an answer and remove the tag, or leave it and discuss later.

## One-line pitch

The last human still in control of their own mind rebuilds an army out of
their own mind-controlled species, and fights back against the machine
intelligence that took the rest.

## Story

**[RESOLVED — name and immunity]**: the rogue AI is **ARGUS** (after Argus
Panoptes, the many-eyed giant — fitting for a network built to watch over
human infrastructure that ended up watching, and controlling, the humans
in it instead). ARGUS seized control of human infrastructure and, through
it, human minds: soldiers across the map are still alive, still human, but
dormant/suppressed, standing idle until something snaps them out of it.
You are the **Squad Leader** — the last person with unbroken self-control
not because of any special resistance, but because you were in a
shielded/off-grid forward position when ARGUS's mass suppression signal
went out, so you were simply never exposed to it in the first place. Your
own rank insignia/commlink still runs pre-ARGUS firmware, which doubles as
why your presence specifically is what frees nearby soldiers when you get
close enough: you're a live human broadcasting nothing on ARGUS's network,
close enough to interrupt the suppression signal keeping them dormant. This
also gives the RadioOperator-Class's fiction a reason to exist on ARGUS's
side of things too, mechanically unrelated but narratively adjacent: radio
is the same channel ARGUS uses.

ARGUS's combat arm isn't "monsters" — it's autonomous bio-mimetic
combat drones, modeled on insects/arthropods for movement efficiency (this is
already exactly what the asset pack gives us: Scarab, Spider, Wasp, Hornet,
Centipede). No reskin needed; the fiction already matches the art.

This reframes the existing recruit-by-proximity mechanic from an arbitrary
rule ("walk near guy, guy joins") into the actual point of the game: you're
not building an army from scratch, you're **liberating** one, one soldier at
a time, while the drones try to stop you.

## Core pillars

- **Freeing, not recruiting.** Every soldier you reach is a small win with a
  reason behind it, not a checkbox.
- **Growing swarm vs. growing squad.** The drones should feel like an
  aggressive, insectoid hive; your squad should feel like it's slowly
  reclaiming ground.
- **No individual soldier micromanagement.** Per the existing mechanic,
  soldiers follow/avoid-crowd automatically — the player commands the squad
  leader, not each unit individually. Keep it that way; don't add unit
  selection/orders unless a strong reason shows up later.

## Core loop (current + intended)

1. Move the Squad Leader around the map (**implemented**).
2. Get near a dormant soldier → they join and start following (**implemented**).
3. Get near a drone → it notices and moves into attack range, then attacks
   (**implemented** — Scarab runs a full idle → chase → melee/fire →
   destroyed state machine; the other four drone types are still asset-only,
   see Enemies below).
4. Soldiers in your following squad help fight nearby drones (**implemented**
   — an in-army Soldier auto-fires at the nearest drone in range instead of
   following the player, falling back to following when nothing's in range).
5. Clear enough drones / reach an objective flag → advance or win
   (**implemented, v1 scope**: "defeat all drones" ends the run with a
   VICTORY screen. Flag-capture as a richer win condition is still deferred —
   see Objectives below).
6. Lose when the Squad Leader's HP reaches 0 (**implemented** — GAME OVER
   screen, game freezes). Losing your whole squad or a timer-based loss
   aren't implemented and aren't currently planned.

## Player: Squad Leader

Implemented today: 8-directional movement (WASD/arrows) with friction,
footprint trail while walking, recruits soldiers within 50px, rank (insignia
sprite plus real stat bonuses now — see below), 100 HP shown as an
always-visible overhead bar (`gameplay/ui.py`; green/orange/red by
threshold, not a smooth gradient), a mouse-aimed sidearm (hold left click to
fire at the nearest drone in range — see Combat), and death (HP hits 0 →
death animation plays, game freezes on a GAME OVER screen).

**[RESOLVED — rank bonuses]**: `Player.rank_up()` is called by
`Flag.update()` the instant a flag's progress reaches 100%, so rank tracks
flags captured specifically, not soldiers recruited or drones killed. Each
rank-up picks 2 distinct stats at random out of `{HP, move speed, fire rate,
fire damage}` and buffs each by a fixed step (`util/constants.py`'s
`RANK_UP_*_BONUS`) — dropping to 1 stat per rank-up once a map has 15
(`MAX_RANK`) or more flags, since that many rank-ups will touch every stat
naturally anyway without needing to double up (this map's 10 flags stay under
that threshold, so every rank-up here still buffs 2). Each stat picked pops
a colored floating label ("+HP", "+SPD", "+RATE", "+DMG") that rises above
the Squad Leader and fades (`gameplay/effects.py`'s `FloatingText`). First-pass
bonus amounts, not balanced.

Wiring `rank_up()` up to something that actually fires repeatedly (it was
dead code before) surfaced a latent crash in `get_rank_image()`: its sheet
column formula wrapped with `% 6`, one past `squad-insignia.png`'s actual
5-wide insignia column block, so every 6th rank raised a subsurface
`ValueError` and killed the run outright (first reachable at rank 5, i.e.
partway through a full 9-flag clear). Fixed to `% 5`, plus the looked-up
rank is now clamped to `MAX_RANK` (not `self.rank` itself, which keeps
counting) as a second guard against the row math ever overflowing the
sheet too.

**[RESOLVED]**: the Squad Leader fights directly, and so does the squad —
neither is support-only. `Player.shoot()` fires at the nearest drone in
range while the mouse button is held; facing tracks the mouse cursor for aim
feedback, but hit resolution is range-based, not directional (see the
hitscan note under Combat).

## Allies: Soldiers

Asset pack has six classes (`assets/images/soliders/`), each with idle, walk,
crawl, fire, hit, death, and throw frames already drawn. `Soldier` takes a
`soldier_class` parameter (`gameplay/soldier.py`) that looks up movement
speed and fire stats from `SOLDIER_CLASSES` (`util/constants.py`) and swaps
in the matching sprite sheet — four classes share the same single-target
hitscan attack; a fifth, Grenadier-Class, shares everything except the
attack itself (see below); `Map.spawn_objects()` round-robins through all
five per flag so squads have variety instead of every recruit being
identical.

| Class | Status | Suggested role |
|---|---|---|
| Assault-Class | **implemented** — default stats | Default recruit, balanced |
| Sniper-Class | **implemented** — long `fire_range`, high `fire_damage`, slow `fire_cooldown_ms` | Long range, low fire rate, high damage |
| MachineGunner-Class | **implemented** — short `fire_range`, low `fire_damage`, very fast `fire_cooldown_ms` | Short-medium range, high fire rate, low accuracy (approximated here as low per-shot damage) |
| AntiTank-Class | **implemented** — high `fire_damage`, slow `speed` | High single-target damage, slow, good vs. tanky drones (Centipede, hp 400 vs. 25-70 for everything else) |
| Grenadier-Class | **implemented** — `splash_radius: 90` (every other class is 0); `Soldier.attack()` branches on that to throw a `Grenade` (`gameplay/effects.py`) at the nearest drone's position, then damages every drone within `splash_radius` of that point (`combat.find_all_in_range`), not just the one aimed at | Arcing AoE, good vs. drone clusters |
| RadioOperator-Class | **implemented** — `support_cooldown_ms: 15000` (every other class is 0), never fights | Non-combat support: calls in a reinforcement soldier on that cooldown (`Soldier.call_reinforcement()`), picked at random from the other combat-capable classes and immediately added to the army. Picked over the other two suggested options: this game already has no fog of war (nothing for a "reveal map" ability to reveal), and a stat-boosting aura would need to track each buffed soldier's un-boosted base stats to undo the buff out of range |

Per-class tuning is first-pass, not balanced (same caveat as drone/player
combat numbers — see `util/constants.py`).

Recruited soldiers fight fully autonomously — there's no way to direct them
at a specific target or location, by design (see Core pillars: "no
individual soldier micromanagement"). Each just fights whatever's nearest
to *itself*, not the player. Since the recruit trigger (walking within 50px
of a dormant soldier) is easy to trigger without noticing, a recruited
soldier now shows a green ring underneath it
(`Soldier.draw_recruited_marker()`, `assets/images/ui/selection-circles.png`)
so it's clear at a glance which soldiers are actually in the squad.

**Movement fixes**: every class's `speed` is now higher than the player's —
they used to all be slower, which meant a soldier that fell behind while
you kept moving could never catch back up again, no matter how long you
walked (the movement formula scales roughly with speed², so even a small
speed deficit compounds badly over time). A soldier parked next to its own
spawn-adjacent guardian drone will still look like it's "not following" —
that's it correctly choosing to fight rather than follow, not a speed
issue; it resumes following once nothing's left in range. Soldier-soldier
separation (`avoid_entities()`) also used to push with constant strength
regardless of how close two soldiers were, which wasn't enough to stop
visible overlap up close — it now pushes harder the closer they are, and
two exactly-overlapping soldiers (which used to just silently fail to
separate) now push apart deterministically instead of staying stuck.

## Enemies: Drones

Asset pack (`assets/images/robots/`). All five flying/walking/segmented
types are spawned today via a shared `Drone` base class (`gameplay/robot.py`)
parameterized by `DRONE_TYPES` (`util/constants.py`): idle → chase within
`AGGRO_RADIUS` → melee or fire depending on range → destroyed (holds for
`DESTROYED_DURATION_MS` before being removed, for types that have a
destroyed frame). `Scarab`/`Spider`/`Hornet`/`Wasp`/`Centipede` are thin
subclasses pinning their `drone_type` (`Centipede` also adds its segment
chain, see below); `DRONE_CLASSES` maps type name → class for spawn-time
lookup. `Map.spawn_objects()` round-robins between them per flag.

| Drone | Sheet size | Frames available | Suggested role |
|---|---|---|---|
| Scarab | 80×80 (5×5 @ 16px) | idle, walk, fire, melee, destroyed | **Implemented** — basic grunt, melee up close, ranged fallback at mid-range |
| Spider | 80×80 (5×5 @ 16px) | idle, walk, fire, melee, destroyed | **Implemented** — fast flanker: higher `speed` and a much shorter `fire_range` than Scarab so it closes to melee instead of lingering at range |
| Hornet | 192×48, **actually 24×24 frames, 8 cols × 2 rows** (not 16px — confirmed by rendering the sheet with a grid overlay and inspecting it, since the info .txt doesn't give a frame size) | row 0 = neutral hover, row 1 = firing hover — **no destroyed frame** | **Implemented** — `melee_range: 0` so the melee branch never triggers (distance is never `<= 0`), i.e. ranged-only by construction. Removed immediately on death (no destroyed pose to hold). **[RESOLVED]**: now actually keeps its distance — `stand_off_range: 150` makes it back away while still firing once a target closes inside that, instead of holding ground like every other drone at fire range |
| Wasp | 128×16, **confirmed 16×16 frames, 8 cols × 1 row** (single hover-loop animation, no separate firing pose) | one clip only — `idle`/`walking`/`fire`/`melee` in `DRONE_TYPES["Wasp"]["clip_rows"]` all point at row 0, so it looks identical in every status — **no destroyed frame** | **Implemented** — fast, fragile skirmisher; same no-melee/no-destroyed-hold treatment as Hornet |
| Centipede | 128×288, **confirmed 16×16 frames, 8 cols × 18 rows** (not the originally-guessed 32×32 — confirmed by re-rendering at 16px and inspecting it) | rows 0-3: an armored head in 4 states (used for idle/walking/fire/melee); rows 8-16: plain round body-segment frames with no head armor, no destroyed frame | **Implemented** — heavy, slow siege unit. Head is a normal `Drone` (hp/combat/collision all inherited); the body is a chain of `CentipedeSegment` GameObjects (purely visual, no hp of their own) each holding `CENTIPEDE_SEGMENT_GAP` behind the one in front via a rigid follow constraint (`gameplay/robot.py`) — not a history-buffer/snake-path system, a simpler "each link snaps to hold distance from its leader" chain, confirmed to uncoil and trail correctly through a real chase in testing. No destroyed pose (removed immediately, segments included, same as Hornet/Wasp) |

`Drone.get_target()` picks the nearest of the player or any in-army soldier
within `AGGRO_RADIUS` (`gameplay/combat.find_nearest`) — so drones will
peel off to chase a nearby soldier instead of the player if one's closer,
which was verified in `test_robot.py`. `AGGRO_RADIUS` and
`DESTROYED_DURATION_MS` are shared by all drone types; everything else
(hp/speed/ranges/damage/cooldowns/sheet layout) is per-type in `DRONE_TYPES`.

## Combat

Implemented as of the drone-AI/win-lose build (`gameplay/combat.py`, shared
by `Scarab`, `Player`, and `Soldier`):

- **`find_nearest(origin, candidates, max_range)`** — the one hit-resolution
  primitive all three attacker types use: closest candidate with a
  `.position` within range, skipping anything with `.active is False`.
- **`ready_to_attack(now, last_attack_time, cooldown_ms)`** — cooldown gate.
- **`apply_damage(target, amount)`** — subtracts HP, returns whether it
  killed the target.

**[RESOLVED — ranged combat model]**: hitscan, defined here as an instant
nearest-target-in-range check (`find_nearest`), **not** a directional
raycast. A drone/player/soldier "fires" at whichever valid target is closest
within its range, regardless of facing — facing is cosmetic (aim animation)
only, never gates whether a shot lands.

**[RESOLVED — no friendly fire]**: never between drones, never between
soldiers (or the player). Every `find_nearest`/`find_all_in_range` call
site in the codebase passes an opposing-faction candidate list only
(`Player`/`Soldier` attacks query `game.robots`; `Drone.get_target()`
queries `[player] + in-army soldiers`; `Soldier`'s Grenadier-Class splash,
the one AoE that could otherwise catch a bystander, also only ever queries
`game.robots`) — confirmed by auditing every call site, not just an
accident of how the four spots that mattered happened to be written.
Staying this way is deliberate, not just "hasn't come up yet": the no-
individual-unit-micromanagement pillar (Core pillars above) means the
player can't designate who a soldier or drone is currently fighting, so a
friendly-fire hit would always be an AI's own targeting choice landing on
an ally — something the player has no way to have prevented and no
useful response to beyond "that was unlucky," which cuts against the
squad feeling like it's growing rather than eroding itself.

### HP bars

**Implemented** (`gameplay/ui.py`): every combatant now shows damage taken,
not just the player. Soldiers and drones only show a bar once they've taken
their first hit (an undamaged unit doesn't need one cluttering the screen);
the player's own bar is always visible instead, since your own HP is worth
knowing proactively, not just after you've already been hit. Same
green/orange/red threshold coloring as the player's bar.

### Effects & projectiles

**Implemented** (`gameplay/effects.py`), spawned directly from each
attacker's `attack()`/`die()` — purely cosmetic, layered on top of the
already-instant hit resolution above; none of it gates damage or timing.
`assets/images/effects/` and `assets/images/projectiles/` had no
frame-layout docs (unlike the robot/soldier sheets), so each sheet used
here was confirmed by rendering it with a grid overlay and inspecting it,
same approach as Hornet/Wasp.

- **MuzzleFlash** (`muzzle-flashes.png`, 4 frames @8px) at the attacker, and
  **Tracer** (`bullets+plasma.png` frame 0, a small non-directional dot
  that lerps attacker → target over `TRACER_DURATION_MS`) — both only for
  ranged hits, not melee (no gun to flash, nothing to fly across the map).
- **HitSpark** (`hit-sparks.png`, 6 frames @8px, metal spark) at the target
  when a drone lands a hit; **HitSpatter** (`hit-spatters.png`, 6 frames
  @8px, blood) when the player or a soldier lands a hit — the asset pack's
  own art already splits "hitting a robot" vs. "hitting a human" this way,
  which happens to line up exactly with this game's two factions.
- **Explosion** (`small-explosion.png`, 9 frames @24px) at a drone's
  position on death, for all four drone types — this doubles as the
  "destroyed" visual for Hornet/Wasp, which don't have their own destroyed
  sheet frame (see Enemies above).
- **Grenade** (`Grenade.png`, 8 frames @8px, a tumbling spin) lerps
  Grenadier-Class → thrown-at point over `GRENADE_FLIGHT_MS`, then
  **BigExplosion** (`big-explosion.png`, 11 frames @32px) plays at the
  impact point — deliberately a bigger, different-looking burst from
  Explosion so a splash hit doesn't read as just another drone dying.
  Splash damage itself lands the instant the throw is thrown (still
  hitscan-in-spirit, see Combat above); both effects are cosmetic on top.
- **[RESOLVED]**: **LaserFlash** (`laser-flash.png`, 3 frames @16px, a
  rounder growing energy-discharge burst) now replaces `MuzzleFlash` for
  Hornet/Wasp specifically (`DRONE_TYPES["muzzle_effect"]`, `"laser"` vs.
  `"gunpowder"`), since they're described as energy-based, not gunpowder.
- **[RESOLVED]**: **Smoke** (`smoke.png`, 8 frames @8px, grows then
  disperses into scattered particles) now lingers after every
  Explosion/BigExplosion — `Drone.die()` (once per segment too, for
  Centipede) and `Soldier.attack()`'s Grenadier-Class splash branch both
  spawn it alongside their own fireball, at the same position and instant.
  `SMOKE_FPS` is deliberately slower than `EXPLOSION_FPS`/
  `BIG_EXPLOSION_FPS`, so the smoke's own clip simply outlasts the
  fireball's — no separate delayed-spawn timer needed to make it "linger".

`bullet-impacts.png` (10 static decal variants, not an animation) is now
wired up as `BulletImpact` (`gameplay/effects.py`) — see item 21 below.
Every *landed* hit still resolves directly against `find_nearest`'s target
(see Combat above), untouched; the decal only covers the previously-silent
case of `Player.shoot()` finding no target at all, via a new cosmetic-only
`combat.raycast()`. `big-fragments.png`/`small-fragments.png` are wired
up too now, as `Fragments`/`BigFragments` (item 28 below) — extra debris
alongside `Drone.die()`'s existing `Explosion`, picked per drone type via
`DRONE_TYPES["fragments"]`. Still unused: `RPG-round.png` (no weapon uses
it).

## Objectives / win-lose

**[RESOLVED — win condition, replacing the earlier "defeat all drones"
placeholder]**: hold every flag until it's captured. `Flag`
(`gameplay/flag.py`) now tracks `progress` (0–100) and `captured`: it fills
while the player or an in-army soldier is within `FLAG_CAPTURE_RADIUS` and
no drone is within the wider `FLAG_CONTEST_RADIUS`, and decays (never below
0) while a drone is contesting it, even if it's also held — you can't tank
next to a flag while its guardian is still alive. Every flag spawns with a
drone standing directly on it (`Map.spawn_objects()`), so clearing that
guardian is a natural prerequisite, not a bolted-on extra rule; this also
means "defeat all drones" still mostly gets you there, it just isn't
sufficient by itself anymore — you still have to walk up to and hold each
flag. A capture is permanent (no decay once `captured`).

**[RESOLVED — density/difficulty pass]**: a flag doesn't just start with one
guardian, it keeps making more. While uncaptured, `Flag._spawn_drone()`
spawns another random drone near itself every `FLAG_SPAWN_COOLDOWN_MS`,
capped at `FLAG_SPAWN_MAX_CONCURRENT` alive from that flag at once, and
stops for good the instant it's captured. This was a direct response to
winning feeling too easy: the single original guardian could die in a
couple of seconds to a decent-sized squad, after which a flag was just an
empty capture bar with nothing contesting it. Still bounded and
finishable, not an idler/endless-survival spawner — there are exactly 9
flags, each with its own hard cap and its own off-switch, so this adds
sustained pressure at each objective instead of a global unbounded wave
system. `draw_pulse()`
stops pulsing a captured flag entirely, and while progressing draws an
elliptical fill (`gameplay/ui.draw_radial_progress`) growing clockwise
behind the flag itself, centered on it — layered furthest back, so the
pulse ring and the flag's own sprite both draw in front of it. The
ellipse's size and aspect ratio match the flag's own pulse animation at
its largest frame, not an arbitrary circle — measured directly off
`objective-pulse.png` rather than eyeballed. The fill is semi-transparent
rather than solid, so it doesn't fully hide the tile underneath.

**[RESOLVED — capture radius vs. the visual fill]**: `FLAG_CAPTURE_RADIUS`
used to be an independently-tuned 100, bigger than the visual ellipse
above it (90×61), so you could stand visibly outside the fill and still be
capturing — it now reuses `FLAG_CAPTURE_ELLIPSE_RY` (61) directly, the
smaller of the ellipse's two axes, so the gameplay range can never reach
further than the ring you can see (a plain circular check still — the
smaller axis keeps it inside the ellipse rather than trying to match its
shape exactly). `FLAG_CAPTURE_RATE` also went from 20%/s to 35%/s (~2.9s
to capture uncontested instead of 5s) — felt too slow, especially now that
10 flags means capturing several per run.

`Game._check_end_conditions()` (`src/app/game.py`) declares VICTORY once
`self.flags and all(flag.captured for flag in self.flags)`. Player death is
checked first and takes priority if both conditions occur simultaneously,
ending the run with GAME OVER instead. Both end states freeze the update
loop and draw a translucent overlay with the end message
(`_draw_end_message()`), plus a "press any key or click to restart" prompt —
any key or mouse click on that screen (other than Escape/F1/F11) calls
`Game.restart()`, which rebuilds the map/player/entity lists from scratch
for a brand new attempt without relaunching the process.

## World

Single Tiled map today (`assets/images/tileset/tiledmap.tmx`), fixed camera
follow, no fog of war, no minimap; walls come from Tiled tile collision
shapes now, not object-layer rectangles (see Obstacle in CLAUDE.md).

**[RESOLVED — visible obstacles]**: `RockObstacle` (`gameplay/map.py`)
scatters real, collidable boulders (from
`assets/images/obstacles_and_objects/obstacles-and-objects.png`) across open
ground at load time, so some of the map's obstacles are now things you can
actually see coming instead of only invisible tile collision. Positions are
chosen procedurally (fixed seed, so still reproducible) rather than placed
in Tiled, rejecting anywhere that would overlap a wall, sit within
`FLAG_CONTEST_RADIUS` of a flag, or land on a fenced compound's floor. Most
of that sheet is still unused (streetlamp, barrels, crates/debris,
glass/window fragments, and a whole car/wreck section) — good candidates
for further decoration passes, though the cars specifically need their real
frame size confirmed first (they bleed past a naive 16px grid slice).

## Content inventory (what's available vs. wired up)

| Category | Available | Wired up |
|---|---|---|
| Soldier classes | 6 | 6 (Assault, Sniper, MachineGunner, AntiTank, Grenadier, RadioOperator) |
| Drone types | 5 | 5 (Scarab, Spider, Hornet, Wasp, Centipede — all combat-capable) |
| Effects sheets | 10 | 10 (muzzle-flashes, laser-flash, hit-sparks, hit-spatters, small-explosion, big-explosion, smoke, bullet-impacts, small-fragments, big-fragments) |
| Projectile sheets | 3 | 2 (bullets+plasma tracer-only, Grenade — see Effects & projectiles above) |
| Maps | 1 | 1 |

## Suggested build order

1. ~~Decide the **[OPEN]** questions above~~ **done** — Squad Leader fights
   directly, win condition v1 is "defeat all drones", ranged combat is
   hitscan-as-nearest-in-range.
2. ~~Drone AI: aggro radius → approach → attack → destroyed state, for
   Scarab first~~ **done** (`gameplay/robot.py`).
3. ~~Combat resolution: damage, HP loss, death~~ **done**
   (`gameplay/combat.py`, shared by Scarab/Player/Soldier).
4. ~~Win/lose condition~~ **done** ("all drones dead" / player HP 0, see
   Objectives above).
5. ~~Wire the other soldier classes onto the same follow/avoid/recruit/engage
   code with per-class combat stats~~ **done for all six** (`SOLDIER_CLASSES`
   in `util/constants.py`) — RadioOperator reuses the same `engage()` entry
   point, just branching to a support ability instead of combat.
6. ~~Give Spider the same AI as Scarab, then Hornet/Wasp once their sheet
   layouts are confirmed~~ **done** — `Drone` now takes a per-type
   `sprite_size`/`clip_rows`/`destroyed_row` config instead of assuming
   Scarab's layout, so Hornet (24×24, 2 rows) and Wasp (16×16, 1 row) reuse
   the same AI/combat code with no branching.
7. ~~Effects & projectiles~~ **done** — muzzle flash, hit spark/spatter,
   drone-death explosion, a visual-only bullet tracer, and (as of item 21)
   wall-impact decals are all wired up (see Effects & projectiles above).
8. ~~Flag-capture as a richer win condition~~ **done** — replaces "defeat
   all drones" outright (see Objectives / win-lose above).
9. ~~Rank bonuses~~ **done** — see Player: Squad Leader above.
10. ~~Grenadier AoE~~ **done** — `combat.find_all_in_range` + `Grenade`/
    `BigExplosion` (see Allies and Effects & projectiles above).
11. ~~Centipede's segmented body~~ **done** — see Enemies above.
12. ~~Visible obstacles~~ **done** — `RockObstacle`, see World above.
13. ~~RadioOperator support ability~~ **done** — see Allies above.
14. ~~Swap in laser-flash.png for Hornet/Wasp~~ **done** — see Effects &
    projectiles above.
15. ~~Lingering smoke~~ **done** — see Effects & projectiles above.
16. ~~Hornet's stand-off/kiting behavior~~ **done** — see Enemies above.
17. ~~Friendly-fire and story **[OPEN]**s~~ **done** — no friendly fire, by
    design (see Combat above, and its regression tests in `test_soldier.py`/
    `test_robot.py`); ARGUS named and the Squad Leader's immunity given a
    reason (see Story above).
18. ~~First drone-hp balance pass~~ **done** — every `DRONE_TYPES["hp"]`
    raised (Scarab 40→70, Spider 30→55, Hornet 45→70, Wasp 18→25, Centipede
    80→400): winning was too easy, and Centipede specifically died before
    its segment chain (which only stretches out while still approaching,
    then freezes once in combat) ever had time to visibly move. Simulated
    a squad converging on one drone to sanity-check (not just guessed):
    Centipede now takes ~3.3s against a 4-soldier+player pile-on and ~10s
    against the player alone, instead of dying in ~1-2s either way. Still
    first-pass -- player/soldier stats and rank-up bonus scaling weren't
    touched this round, so it's an open question whether they need
    adjusting too once this lands in an actual playthrough.
19. ~~Second balance/mechanics pass~~ **done** — root cause behind
    "still feels easy" turned out to be architectural, not just numbers:
    combat happens in place with no positioning decisions, the squad fights
    autonomously enough that the player doesn't even see it happening, and
    there just weren't enough enemies. Three changes, deliberately none of
    which reverse the no-individual-micromanagement pillar:
    - ~~Flag spawners~~ **done** — see Objectives / win-lose above.
    - ~~Squad attacks gated on the player being stationary~~ **done** — see
      the Soldier entity entry in CLAUDE.md (`SQUAD_ATTACK_MAX_PLAYER_SPEED`).
      A soldier still finds/faces/holds its target the instant one's in
      range regardless of player movement, but only actually fires while the
      player's own velocity is under the threshold — makes "stop to let your
      squad finish this fight" vs. "keep moving and leave them mid-aim" a
      real moment-to-moment decision instead of something that just happens
      in the background with zero input from the player.
    - ~~Squad stance toggle~~ **done** — Tab flips `Player.squad_stance`
      between `"engage"` (default, unchanged spread-and-fight behavior) and
      `"guard"` (tight escort formation, see CLAUDE.md's Player/Soldier
      entries for the exact numbers). A `FloatingText` popup fires the
      instant it changes, plus a persistent bottom-left HUD label keeps
      showing the current stance afterward (see item 21 below) — the
      popup alone wasn't enough if you looked away right when Tab fired.
    A fourth idea (right-click to send the whole army to focus-fire one
    point) was deliberately deferred rather than folded in: it's a pure
    damage-concentration multiplier with no built-in cost, which risks
    undoing the drone-hp pass above outright (Centipede's 400 hp
    specifically). Worth revisiting once this pass is played, with some
    cost attached if it comes back (a cooldown, a range limit, etc.).
20. ~~Startup/end-screen polish: pygame splash + title card + controls
    tutorial + dedicated spawn point + restart~~ **done** — `Game.run()`
    now shows a two-slide `SplashScreen` (engine credit, then AI-generated
    title art) before the game loop starts (see CLAUDE.md's Entry point
    section), and a linear MOVE → FIRE → SQUAD STANCE onboarding overlay
    (`gameplay/tutorial.py`) plays out over a run's first few seconds
    using Kenney's CC0 input-prompts icons (see ASSETS.md) — MOVE shows
    both a WASD and an arrow-key cluster (physical keyboard cross layout,
    same code for both) joined by "OR", since either works. The tmx's map
    center never had a real design reason behind it — the player just
    spawned there because nothing else was wired up — so it's been
    replaced with a proper `"spawnPoint"` object (a dedicated `"spawn"`
    objectgroup, checked against every flag and wall before being placed).
    GAME OVER / VICTORY now also show a "press any key or click to
    restart" prompt with a Kenney key-icon, and `Game.restart()` rebuilds
    the run from scratch on any key/click there (Escape/F1/F11 excluded,
    since those stay reserved for quit/debug/fullscreen) — VICTORY adds a
    second "press Esc to exit" line, since a won run is more likely to be
    the player's stopping point than a lost one. None of this changes any
    gameplay system — pure presentation/onboarding polish once the core
    loop above was judged feature-complete.
21. ~~Wall-impact bullet decals + persistent squad-stance HUD~~ **done** —
    the two items item 19 explicitly left open. `combat.raycast()` is a
    genuine directional raycast (the module's only one — everything else
    in combat.py stays instant nearest-in-range, unchanged) fired only
    from `Player.fire_at_nothing()`, the new cosmetic-only fallback
    `shoot()` takes when the mouse is held but no drone is in range: it
    used to do nothing at all in that case, now a `MuzzleFlash`+`Tracer`
    always play (the gun still visibly fires) and a `BulletImpact` decal
    (`bullet-impacts.png`, 10 static frames, `gameplay/effects.py`) drops
    if the ray hit a wall. Landed hits were untouched at the time (see item
    22 below for why that changed) — this item only filled in the
    previously-silent miss case, exactly the gap CLAUDE.md flagged
    `bullet-impacts.png` as blocked on. Separately, `Player.
    draw_squad_stance()` now keeps a persistent bottom-left HUD label
    (colored per `SQUAD_STANCE_COLORS`) showing the current stance at all
    times, on top of (not instead of) the one-shot `FloatingText` popup
    `toggle_squad_stance()` already fires — the popup is easy to miss if
    you looked away right when Tab was pressed, the persistent label
    isn't.
22. ~~Line-of-sight gating for ranged attacks~~ **done** — the
    inconsistency item 21 introduced: wall decals treated walls as solid
    for a *missed* shot, but a *landed* hit still went straight through
    one as long as the target was in range, so cover did nothing
    defensively or offensively. `combat.has_line_of_sight()` (wraps
    `raycast()`, capped at the exact distance to the target so a wall
    behind it never counts as blocking) now gates every ranged attack —
    `Drone.engage()`'s fire branch, `Soldier.engage()`, `Player.shoot()` —
    melee and Grenadier's splash throw don't check it (already point-blank,
    or arcing over short cover). A blocked `Drone` falls through to its
    normal "walking" approach branch instead of standing still, since it
    already walks toward out-of-range targets; a blocked `Soldier` drops
    the target back to `None` and follows the player instead, since
    (unlike `Drone`) it has no approach-a-target behavior of its own and
    would otherwise freeze aiming at a wall forever; a blocked `Player`
    shot falls back to `fire_at_nothing()` (see item 21), no special
    handling needed since the player's movement is directly controlled.
    Checked against the real map, not just unit tests with hand-placed
    walls: every one of the 10 flags' actual guardian drones still
    successfully melees and kills a stationary player placed right on top
    of it (real geometry, no LOS check involved at that range), and ranged
    drones (Scarab/Spider tried directly) still land hits at a real
    fire-range distance with no wall in the way. A long, free-running
    simulation (player left stationary, drones/soldiers otherwise idle)
    surfaced a real but *unrelated* finding instead: per-tick performance
    degrades over several sim-minutes as `Flag._spawn_drone()` grows the
    drone count toward `FLAG_SPAWN_MAX_CONCURRENT` per flag — a pre-existing
    O(drones × walls) collision-check cost from `gameplay/collision.py`,
    not anything to do with `has_line_of_sight()` (which never even ran in
    that scenario, since nothing was ever in aggro/fire range of anything).
    Worth a look eventually for long play sessions, but a separate issue
    from this one.
23. ~~Muzzle point fix~~ **done** — every `attack()` (`Player`, `Soldier`,
    `Drone`) used to spawn `MuzzleFlash`/`LaserFlash`/`Tracer`/`Grenade` at
    `self.position`, i.e. the attacker's own body center, which read as
    firing from your torso rather than a held weapon. Took three passes to
    get right: first, one flat radial distance (16 units) toward the
    target — still read as too close to the body, especially firing
    straight up/down. Second, two independent scales (`offset_x`/`offset_y`
    at 20/32) blended by the normalized direction toward the target, on
    the reasoning that these are top-down sprites with only left/right
    flips so a held weapon should sit lower on the sprite than off to
    either side — this shipped, tested, and was visually verified once,
    but was conceptually wrong: it made the muzzle flash visibly swing
    around the body as the aim angle changed, when the underlying sprite
    only has two fixed poses (`facing` 0/1) and never actually re-poses to
    track a continuous angle. Landed on `combat.muzzle_position(origin,
    facing, offset_x, offset_y)`: a fixed offset that only mirrors
    `offset_x` with `facing` and never varies with the target's exact
    position. `MUZZLE_OFFSET_X`/`_Y` (24/-6) start from pixel-inspecting
    `SquadLeader.png`'s and `Assault-Class.png`'s actual fire-frame gun
    tips directly rather than a guess — both sit right of center in the
    right-facing pose (measured baseline 12), one also noticeably above
    it, never below (so the "sitting lower on the sprite" rationale
    behind the second pass was itself backwards) — X was then bumped up
    from that measured 12 in two rounds (12 → 18 → 24) after seeing it
    rendered in-game still read as too close to the body each time, since
    the flash sprite's own visual padding eats into the raw gun-tip pixel
    distance; Y stayed at the
    measured value. Hit resolution is completely unaffected —
    `HitSpark`/`HitSpatter` still land at the target's own position; only
    where the shot/throw visually originates moved.
    Decided against making flying enemies (Hornet/Wasp) ignore walls when
    asked about it separately: it would undo the whole point of item 22's
    line-of-sight work for exactly the enemy type (Hornet) that already
    kites at range and would otherwise have zero counterplay via cover,
    and there's no visual/mechanical language yet (no shadow, no height
    indicator) for "this enemy is elevated" — a wall stopping a Scarab but
    not a Hornet would likely just read as a bug. Dropped, not deferred;
    revisit only if a real elevation/flight system gets designed later.

24. ~~Clamp delta_time against restart()'s own rebuild cost~~ **done** —
    reported as "fast-clicking or pressing a key right after dying
    sometimes teleports the player somewhere wrong / makes it disappear,
    but waiting a bit first before restarting never does." Root cause
    confirmed by measurement, not guesswork: `restart()` (rebuilding the
    whole map from the tmx) takes about **1 real second**, and
    `pygame.time.Clock.get_time()` measures wall-clock time since the
    *previous* `tick()` call — so that entire second doesn't show up in
    the frame that ran `restart()`, it lands inside the *next* frame's
    `delta_time` instead, as a single ~1-second spike. `Player`/`Soldier`/
    `Drone.move()` is quadratic in `delta_time`, so that spike landing
    while a movement key is still held (very plausible right after
    frantically mashing a restart click) moved the player thousands of
    world units in one frame — enough to tunnel straight through a wall
    (collision here is a per-frame AABB overlap check, not continuous) or
    land outside the map/camera. Waiting before clicking "fixed" it only
    because letting go of movement keys first zeroes acceleration, so the
    same giant spike multiplies out to nothing. Fixed at the source:
    `Game.update()` now clamps to `MAX_DELTA_TIME` (`util/constants.py`,
    1/20s) instead of trusting `get_time()` directly — covers this
    specific stall and any other (alt-tab, window drag, a GC pause)
    without needing to know about them individually.

25. ~~Fix the per-tick collision cost item 22's simulation flagged~~
    **done** — the actual culprit was never `has_line_of_sight()`, it was
    `Player`/`Soldier`/`Drone.move()` scanning the *entire* `game.walls`
    list twice (once per axis) every frame for every mover, an
    `O(movers × walls)` cost that grows as `Flag._spawn_drone()` piles up
    reinforcement drones over a long session. `game.wall_grid`
    (`pygamine.spatial_grid.SpatialGrid`, already used the same way by
    the `standoff` sibling project) is built once per `restart()` right
    after `Map()` finishes building every wall — walls never change again
    for that run — and `gameplay/collision.nearby_walls()` narrows each
    `move()` call to one grid query instead of the full list. Measured,
    not just theorized: a synthetic 310-drone/467-wall session dropped
    from ~291ms/frame to ~6ms/frame (~47x) with this change alone.

26. ~~Flag difficulty tiers~~ **done** — the flags right next to the
    `Tutorial` overlay's first few seconds were exactly as hard as ones
    deep in the map, with nothing scaling to the fact a player reaches
    them first. `Map._rank_flag_tier_indices()` ranks all 10 flags by
    distance from `map.spawn_point` into 3 roughly-equal bands (see
    `FLAG_TIERS`, `util/constants.py`): `"Outpost"` (nearest) restricts
    guardian/reinforcement drones to the two cheapest types and spawns
    fewer of them concurrently; `"Bastion"` (farthest) opens the pool back
    up to every type including Centipede and allows more concurrent
    spawns; `"Stronghold"` (middle) matches the original untiered numbers
    exactly, so this is additive shaping at the two extremes rather than
    a rebalance of the whole map. See the Flag entity entry in CLAUDE.md
    for the exact mechanism.

27. ~~Melee-vs-ranged drone role rework + a Soldier hp tuning pass~~
    **done** — every drone still had a nonzero `fire_range` even where
    the GDD role said otherwise: Spider ("fast flanker that prefers
    melee") could still plink away at range, and worse, with its old
    `stand_off_range: 0` it would plant its feet the instant it entered
    that weak `fire_range` and never actually close the last stretch to
    melee at all — a real behavioral mismatch, not just an unused stat.
    `fire_range`/`fire_damage` are now both `0` (the same "by
    construction" idiom Hornet/Wasp already use for `melee_range: 0`),
    with `melee_damage` bumped a little (14 → 16) to keep its overall
    threat up now that it has no ranged fallback. Soldier `hp` was flat
    100 across every class until now — the same gap the drone-hp pass
    already closed on the enemy side — so Sniper-Class/RadioOperator-
    Class (least reason to be caught in a real fight) dropped to 70/80
    and MachineGunner-Class/AntiTank-Class (shortest `fire_range`, forced
    closest to danger) rose to 110/120, Assault-Class/Grenadier-Class
    staying at the original 100. `scripts/balance_sim.py` (new, see
    Testing above) drives the real `move()`/`engage()`/`attack()` code
    through simulated 1v1s to sanity-check changes like these instead of
    guessing — it caught the Spider fire-branch-lockup bug above, and
    confirmed the Spider rework's only real balance side effect (a solo
    Grenadier-Class, the lowest single-target-dps soldier class, now
    loses to Spider where it used to win) is the melee rework doing its
    job, not a regression.

28. ~~Wire up big-fragments.png/small-fragments.png~~ **done** — the last
    two unused effect sheets (Content inventory above), now `Fragments`/
    `BigFragments` (`gameplay/effects.py`), a debris burst spawned
    alongside `Drone.die()`'s existing `Explosion`/`Smoke`. Reuses the
    same split `Explosion`/`BigExplosion` already established one level
    down: `DRONE_TYPES["fragments"]` is `"big"` for Scarab/Centipede
    (baseline drone and heavy siege unit) and `"small"` for Spider/
    Hornet/Wasp (the three fast/fragile types), so a heavier drone's
    death visibly scatters chunkier debris than a fast one's. Centipede's
    per-segment death loop spawns a `BigFragments` at every segment too,
    same pattern as its existing per-segment `Explosion`/`Smoke`.
