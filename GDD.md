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
   (**not implemented** — Scarab/Spider/Wasp/Hornet currently just idle or
   roam with no AI at all).
4. Soldiers in your following squad help fight nearby drones (**not
   implemented** — Soldier has no combat code yet, only follow/avoid).
5. Clear enough drones / reach an objective flag → advance or win
   (**not implemented** — Flag entities exist on the map and pulse, but do
   nothing on reach; no win condition exists at all yet).
6. Lose if **[OPEN]** — HP hits 0? Losing your whole squad? A timer? Nothing
   currently reduces player HP; `Player.hp` exists but nothing decreases it.

## Player: Squad Leader

Implemented today: 8-directional movement (WASD/arrows) with friction,
footprint trail while walking, recruits soldiers within 50px, rank
(`rank_up()`, insignia sprite, no gameplay effect yet), 100 HP field (unused).

Not implemented: attacking, taking damage, dying, any effect from rank
beyond the icon.

**[OPEN]**: Does the Squad Leader fight directly, or are they support-only
(the soldiers do all the fighting, you're the objective drones want to kill)?
Both are valid games — the first is closer to an action-RTS hybrid, the
second makes every step genuinely tense since losing you probably ends the
run. Pick one; it changes a lot of downstream balance.

## Allies: Soldiers

Asset pack has six classes (`assets/images/soliders/`), each with idle, walk,
crawl, fire, hit, death, and throw frames already drawn. Only one is wired up.

| Class | Status | Suggested role |
|---|---|---|
| Assault-Class | **implemented** (generic follow/avoid only, no combat) | Default recruit, balanced |
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
Only Scarab is spawned today, and it has no AI at all — idle animation only.

| Drone | Sheet size | Frames available | Suggested role |
|---|---|---|---|
| Scarab | 80×80 (5×5 @ 16px) | idle, walk, fire, melee, destroyed | Basic grunt — melee up close, weak ranged fallback |
| Spider | 80×80 (5×5 @ 16px) | idle, walk, fire, melee, destroyed | Fast flanker, prefers melee |
| Hornet | 192×48 | neutral hover, firing hover (undocumented row count/width — more columns than Scarab, likely a smoother hover loop) | Flying, ranged only, no melee frame so keeps distance |
| Wasp | 128×16 (single row) | **[OPEN — not in Robot animation info.txt; only one row, so likely a single held pose/loop rather than idle+walk+attack]** | Flying, likely ranged skirmisher — needs a source check before committing to this role |
| Centipede | 128×288 | **[OPEN — not in Robot animation info.txt; unusually tall sheet, doesn't fit the 16px-row assumption the others use — may be a segmented/modular body (head/body/tail pieces) rather than simple animation rows]** | Segmented/heavy — good siege-unit candidate, but figure out the actual sprite layout first |

Minimum viable drone AI: idle until player/squad within an aggro radius →
walk into attack range → play fire or melee (whichever the sprite has, prefer
ranged if both) → repeat, with a destroyed state on death instead of just
disappearing. This mirrors the Soldier chase/avoid code already written
(`gameplay/soldier.py`) — the pattern (chase beyond a distance, hold within
it) is directly reusable.

## Combat (not yet designed in detail)

Unused but present assets ready for this: `assets/Effects/` (explosions,
muzzle flashes, hit sparks/spatters, smoke), `assets/Projectiles/`
(bullets+plasma, grenade, RPG round). `gameplay/collision.py`'s AABB
resolution already exists for movement collision and could plausibly be
reused/adapted for hitscan or projectile-vs-entity checks.

**[OPEN]** questions before implementing:
- Ranged combat: hitscan, or simulated projectiles (`Projectiles/` assets
  suggest the latter was the original intent)?
- Friendly fire between drones, or between soldiers?
- Does the Squad Leader have a weapon, or are they unarmed (ties into the
  support-only question above)?

## Objectives / win-lose (currently nonexistent)

`Flag` entities already spawn from the Tiled map's object layer and pulse,
but `flag.py` has no logic beyond the pulse animation — reaching one does
nothing. **[OPEN]**: is the win condition "reach/hold all flags", "clear all
drones", or something else? Given the pillars above (grow the squad, reclaim
ground), "hold a flag until it's fully captured, drones will contest it"
fits well, but "defeat all drones" is simpler to build first and could be a
placeholder win condition to ship before the flag-capture system exists.

## World

Single Tiled map today (`assets/images/tileset/tiledmap.tmx`), fixed camera
follow, no fog of war, no minimap. `Obstacles and Objects` sheet is unused
beyond the invisible collision walls already spawned from "wall" objects in
the map — there may be room to make some of those visible/decorative instead
of invisible-only.

## Content inventory (what's available vs. wired up)

| Category | Available | Wired up |
|---|---|---|
| Soldier classes | 6 | 1 (Assault, non-combat) |
| Drone types | 5 | 1 (Scarab, non-combat) |
| Effects sheets | 10 | 0 |
| Projectile sheets | 3 | 0 |
| Maps | 1 | 1 |

## Suggested build order

1. Decide the **[OPEN]** questions above (at minimum: Squad Leader fights or
   not, win condition placeholder, ranged combat model).
2. Drone AI: aggro radius → approach → attack → destroyed state, for Scarab
   first (reuses the Soldier chase/hold-distance pattern).
3. Combat resolution: damage, HP loss, death, using the existing HP field on
   `Player`/`Soldier` and a new one on drones.
4. Wire the other 5 soldier classes onto the same follow/avoid/recruit code
   with per-class combat stats.
5. Win/lose condition (start with "all drones dead" if flag-capture is too
   much for a first pass).
6. Only then: polish (effects, projectiles, visible obstacles, RadioOperator
   support ability, rank bonuses).
