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
(`rank_up()`, insignia sprite, no gameplay effect yet), 100 HP, a mouse-aimed
sidearm (hold left click to fire at the nearest drone in range — see Combat),
and death (HP hits 0 → death animation plays, game freezes on a GAME OVER
screen).

Not implemented: any effect from rank beyond the icon.

**[RESOLVED]**: the Squad Leader fights directly, and so does the squad —
neither is support-only. `Player.shoot()` fires at the nearest drone in
range while the mouse button is held; facing tracks the mouse cursor for aim
feedback, but hit resolution is range-based, not directional (see the
hitscan note under Combat).

## Allies: Soldiers

Asset pack has six classes (`assets/images/soliders/`), each with idle, walk,
crawl, fire, hit, death, and throw frames already drawn. Only one is wired up.

| Class | Status | Suggested role |
|---|---|---|
| Assault-Class | **implemented** (follow/avoid/recruit + auto-fire on the nearest in-range drone, `SOLDIER_FIRE_RANGE`/`SOLDIER_FIRE_DAMAGE` in `util/constants.py`) | Default recruit, balanced |
| Sniper-Class | asset only | Long range, low fire rate, high damage |
| MachineGunner-Class | asset only | Short-medium range, high fire rate, low accuracy |
| Grenadier-Class | asset only | Arcing AoE, good vs. drone clusters |
| AntiTank-Class | asset only | High single-target damage, slow, good vs. tanky drones (Centipede?) |
| RadioOperator-Class | asset only | Non-combat support — **[OPEN]**: calls in reinforcements? Reveals map? Boosts nearby squad? |

All six sharing the follow/avoid/recruit code already written for
Assault-Class is the obvious first step — the class only needs to change
which sprite sheet and which attack behavior gets attached.

## Enemies: Drones

Asset pack (`assets/images/robots/`), animation info confirms combat frames
already exist for most of them (idle, walk, **firing**, **melee**,
**destroyed** for Scarab/Spider; neutral hover + firing hover for Hornet).
Only Scarab is spawned today. It now has a full combat AI
(`gameplay/robot.py`): idle → chase within `AGGRO_RADIUS` → melee or fire
depending on range → destroyed (holds for `DESTROYED_DURATION_MS` before
being removed).

| Drone | Sheet size | Frames available | Suggested role |
|---|---|---|---|
| Scarab | 80×80 (5×5 @ 16px) | idle, walk, fire, melee, destroyed | **Implemented** — basic grunt, melee up close, ranged fallback at mid-range |
| Spider | 80×80 (5×5 @ 16px) | idle, walk, fire, melee, destroyed | Fast flanker, prefers melee — same sheet layout as Scarab, should be a near-copy of `Scarab`/`robot.py` once art is swapped in |
| Hornet | 192×48 | neutral hover, firing hover (undocumented row count/width — more columns than Scarab, likely a smoother hover loop) | Flying, ranged only, no melee frame so keeps distance |
| Wasp | 128×16 (single row) | **[OPEN — not in Robot animation info.txt; only one row, so likely a single held pose/loop rather than idle+walk+attack]** | Flying, likely ranged skirmisher — needs a source check before committing to this role |
| Centipede | 128×288 | **[OPEN — not in Robot animation info.txt; unusually tall sheet, doesn't fit the 16px-row assumption the others use — may be a segmented/modular body (head/body/tail pieces) rather than simple animation rows]** | Segmented/heavy — good siege-unit candidate, but figure out the actual sprite layout first |

`Scarab.get_target()` picks the nearest of the player or any in-army soldier
within `AGGRO_RADIUS` (`gameplay/combat.find_nearest`) — so drones will
peel off to chase a nearby soldier instead of the player if one's closer,
which was verified in `test_robot.py`.

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
only, never gates whether a shot lands. Simulated projectile objects using
the unused `assets/Projectiles/` sheets (bullets, grenade, RPG round) are
deferred to a later pass; `Effects/` (muzzle flash, hit sparks, explosions)
are similarly unused and deferred as visual polish on top of the existing
hit resolution.

**[OPEN]**: friendly fire between drones, or between soldiers — not
implemented either way; `find_nearest` is currently only ever called with an
opposing-faction candidate list, so there's no accidental friendly fire to
worry about, but it's also not a deliberate design decision yet.

## Objectives / win-lose

`Flag` entities still spawn from the Tiled map's object layer and pulse, but
`flag.py` has no logic beyond the pulse animation — reaching one still does
nothing. **[RESOLVED — v1 win condition]**: "defeat all drones."
`Game._check_end_conditions()` (`src/app/game.py`) latches
`_robots_ever_present` the first time any drone exists, then declares
VICTORY once the robots list is empty again (this guards against a false
victory before any drones have spawned). Player death is checked first and
takes priority if both conditions occur simultaneously, ending the run with
GAME OVER instead. Both end states freeze the update loop and draw a
translucent overlay with the end message (`_draw_end_message()`).

Flag-capture as a richer/alternate win condition (hold a flag while drones
contest it) is still deferred — "defeat all drones" was deliberately chosen
as the simpler placeholder to ship a playable loop first, per the build
order below.

## World

Single Tiled map today (`assets/images/tileset/tiledmap.tmx`), fixed camera
follow, no fog of war, no minimap. `Obstacles and Objects` sheet is unused
beyond the invisible collision walls already spawned from "wall" objects in
the map — there may be room to make some of those visible/decorative instead
of invisible-only.

## Content inventory (what's available vs. wired up)

| Category | Available | Wired up |
|---|---|---|
| Soldier classes | 6 | 1 (Assault, combat-capable) |
| Drone types | 5 | 1 (Scarab, combat-capable) |
| Effects sheets | 10 | 0 |
| Projectile sheets | 3 | 0 |
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
5. **Next up:** wire the other 5 soldier classes onto the same
   follow/avoid/recruit/engage code with per-class combat stats (ranges,
   damage, cooldowns already parameterized per-attacker in
   `util/constants.py`, so this is mostly new stat blocks + sprite sheets,
   not new logic).
6. Then: give Spider the same AI as Scarab (identical 80×80/5×5 sheet
   layout), then Hornet/Wasp/Centipede once their sheet layouts are
   confirmed (see the **[OPEN]** rows in Enemies above).
7. Only then: polish (effects, projectiles, visible obstacles, RadioOperator
   support ability, rank bonuses, flag-capture as a richer win condition).
