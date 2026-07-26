# Artificial Chaos — Game Design Document

Living document. Update it whenever a design decision is made so it doesn't
get lost between sessions again. Anything marked **[OPEN]** is an unresolved
question — pick an answer and remove the tag, or leave it and discuss later.

## One-line pitch

The last human still in control of their own mind rebuilds an army out of
their own mind-controlled species, and fights back against the machine
intelligence that took the rest.

## Story

A rogue AI — working name **the Convergence** **[OPEN: needs a real name]** —
seized control of human infrastructure and, through it, human minds: soldiers
across the map are still alive, still human, but dormant/suppressed, standing
idle until something snaps them out of it. You are the **Squad Leader**, the
last person with unbroken self-control (why you specifically are immune is
**[OPEN]** — a implant malfunction, a shielded bunker, natural resistance,
whatever fits) and your presence is what frees nearby soldiers when you get
close enough.

The Convergence's combat arm isn't "monsters" — it's autonomous bio-mimetic
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
footprint trail while walking, recruits soldiers within 50px, rank
(`rank_up()`, insignia sprite, no gameplay effect yet), 100 HP shown as an
always-visible overhead bar (`gameplay/ui.py`; green/orange/red by
threshold, not a smooth gradient), a mouse-aimed sidearm (hold left click to
fire at the nearest drone in range — see Combat), and death (HP hits 0 →
death animation plays, game freezes on a GAME OVER screen).

Not implemented: any effect from rank beyond the icon.

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
hitscan attack and are wired up this way; `Map.spawn_objects()` round-robins
through them per flag so squads have variety instead of every recruit being
identical.

| Class | Status | Suggested role |
|---|---|---|
| Assault-Class | **implemented** — default stats | Default recruit, balanced |
| Sniper-Class | **implemented** — long `fire_range`, high `fire_damage`, slow `fire_cooldown_ms` | Long range, low fire rate, high damage |
| MachineGunner-Class | **implemented** — short `fire_range`, low `fire_damage`, very fast `fire_cooldown_ms` | Short-medium range, high fire rate, low accuracy (approximated here as low per-shot damage) |
| AntiTank-Class | **implemented** — high `fire_damage`, slow `speed` | High single-target damage, slow, good vs. tanky drones (Centipede?) |
| Grenadier-Class | asset only — **not implemented**, needs a real AoE mechanic (splash damage against multiple targets) that `gameplay/combat.py`'s single-target `find_nearest`/`apply_damage` doesn't support yet | Arcing AoE, good vs. drone clusters |
| RadioOperator-Class | asset only — **not implemented** | Non-combat support — **[OPEN]**: calls in reinforcements? Reveals map? Boosts nearby squad? |

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

## Enemies: Drones

Asset pack (`assets/images/robots/`). All four flying/walking types are
spawned today via a shared `Drone` base class (`gameplay/robot.py`)
parameterized by `DRONE_TYPES` (`util/constants.py`): idle → chase within
`AGGRO_RADIUS` → melee or fire depending on range → destroyed (holds for
`DESTROYED_DURATION_MS` before being removed, for types that have a
destroyed frame). `Scarab`/`Spider`/`Hornet`/`Wasp` are thin subclasses
pinning their `drone_type`; `DRONE_CLASSES` maps type name → class for
spawn-time lookup. `Map.spawn_objects()` round-robins between them per flag.

| Drone | Sheet size | Frames available | Suggested role |
|---|---|---|---|
| Scarab | 80×80 (5×5 @ 16px) | idle, walk, fire, melee, destroyed | **Implemented** — basic grunt, melee up close, ranged fallback at mid-range |
| Spider | 80×80 (5×5 @ 16px) | idle, walk, fire, melee, destroyed | **Implemented** — fast flanker: higher `speed` and a much shorter `fire_range` than Scarab so it closes to melee instead of lingering at range |
| Hornet | 192×48, **actually 24×24 frames, 8 cols × 2 rows** (not 16px — confirmed by rendering the sheet with a grid overlay and inspecting it, since the info .txt doesn't give a frame size) | row 0 = neutral hover, row 1 = firing hover — **no destroyed frame** | **Implemented** — `melee_range: 0` so the melee branch never triggers (distance is never `<= 0`), i.e. ranged-only by construction. Removed immediately on death (no destroyed pose to hold). Doesn't yet actively keep its distance when a target closes in — it still just chases/holds like the others; a real stand-off/kiting behavior is a further-out polish item, not implemented |
| Wasp | 128×16, **confirmed 16×16 frames, 8 cols × 1 row** (single hover-loop animation, no separate firing pose) | one clip only — `idle`/`walking`/`fire`/`melee` in `DRONE_TYPES["Wasp"]["clip_rows"]` all point at row 0, so it looks identical in every status — **no destroyed frame** | **Implemented** — fast, fragile skirmisher; same no-melee/no-destroyed-hold treatment as Hornet |
| Centipede | 128×288 | **[OPEN — still not wired up]**: gridding the sheet at 32×32 shows ~9 rows of distinct rolled-up/mandible poses, plus a trailing row of small 16×16 icons and a partial row of extra segment-looking pieces below the main grid — consistent with the original guess that this is a modular/segmented body (a head sprite plus repeatable body-segment pieces), not a simple animation grid `Drone` can slice with `add_directional_clips`. Wiring it up means designing how a segmented body renders/moves, not just adding a `DRONE_TYPES` entry — a bigger, separate task from Hornet/Wasp | Segmented/heavy — good siege-unit candidate once the rendering approach is designed |

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

**[OPEN]**: friendly fire between drones, or between soldiers — not
implemented either way; `find_nearest` is currently only ever called with an
opposing-faction candidate list, so there's no accidental friendly fire to
worry about, but it's also not a deliberate design decision yet.

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

Still unused: `laser-flash.png` (a rounder energy-weapon flash — could
replace `muzzle-flashes.png` for Hornet/Wasp specifically, since they're
described as energy-based, not gunpowder), `big-explosion.png`/
`big-fragments.png`/`small-fragments.png`/`smoke.png`/`bullet-impacts.png`
(debris/smoke lingering after an explosion, or ground scorch marks —
polish, not required for the core loop), and `Grenade.png`/`RPG-round.png`
(no AoE weapon exists yet — same blocker as Grenadier-Class, see Allies
above).

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
flag. A capture is permanent (no decay once `captured`). `draw_pulse()`
stops pulsing a captured flag entirely, and while progressing draws an
elliptical fill (`gameplay/ui.draw_radial_progress`) growing clockwise
behind the flag itself, centered on it — layered furthest back, so the
pulse ring and the flag's own sprite both draw in front of it. The
ellipse's size and aspect ratio match the flag's own pulse animation at
its largest frame, not an arbitrary circle — measured directly off
`objective-pulse.png` rather than eyeballed. The fill is semi-transparent
rather than solid, so it doesn't fully hide the tile underneath.

`Game._check_end_conditions()` (`src/app/game.py`) declares VICTORY once
`self.flags and all(flag.captured for flag in self.flags)`. Player death is
checked first and takes priority if both conditions occur simultaneously,
ending the run with GAME OVER instead. Both end states freeze the update
loop and draw a translucent overlay with the end message
(`_draw_end_message()`).

## World

Single Tiled map today (`assets/images/tileset/tiledmap.tmx`), fixed camera
follow, no fog of war, no minimap. `assets/images/obstacles_and_objects/`
is unused beyond the invisible collision walls already spawned from "wall"
objects in the map — there may be room to make some of those
visible/decorative instead of invisible-only.

## Content inventory (what's available vs. wired up)

| Category | Available | Wired up |
|---|---|---|
| Soldier classes | 6 | 4 (Assault, Sniper, MachineGunner, AntiTank — all combat-capable) |
| Drone types | 5 | 4 (Scarab, Spider, Hornet, Wasp — all combat-capable) |
| Effects sheets | 10 | 4 (muzzle-flashes, hit-sparks, hit-spatters, small-explosion) |
| Projectile sheets | 3 | 1 (bullets+plasma, tracer-only — see Effects & projectiles above) |
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
   code with per-class combat stats~~ **done for Assault/Sniper/
   MachineGunner/AntiTank** (`SOLDIER_CLASSES` in `util/constants.py`).
   Grenadier and RadioOperator still need new mechanics (AoE, a support
   ability) the current single-target hitscan model doesn't cover.
6. ~~Give Spider the same AI as Scarab, then Hornet/Wasp once their sheet
   layouts are confirmed~~ **done** — `Drone` now takes a per-type
   `sprite_size`/`clip_rows`/`destroyed_row` config instead of assuming
   Scarab's layout, so Hornet (24×24, 2 rows) and Wasp (16×16, 1 row) reuse
   the same AI/combat code with no branching. Only Centipede remains
   unwired (see the **[OPEN]** row in Enemies above — it needs a modular/
   segmented-body rendering approach, not just a stat block).
7. ~~Effects & projectiles~~ **started** — muzzle flash, hit spark/spatter,
   drone-death explosion, and a visual-only bullet tracer are all wired up
   (see Effects & projectiles above). Still open within this bucket: swap
   in `laser-flash.png` for Hornet/Wasp's muzzle flash, lingering
   smoke/scorch decals, and impact marks on walls (`bullet-impacts.png`).
8. ~~Flag-capture as a richer win condition~~ **done** — replaces "defeat
   all drones" outright (see Objectives / win-lose above).
9. **Next up:** the rest of polish (visible obstacles, RadioOperator
   support ability, Grenadier AoE + `Grenade.png`/`RPG-round.png`, rank
   bonuses, Centipede's segmented body).
