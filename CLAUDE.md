# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See [GDD.md](GDD.md) for story/design intent — this file is architecture only.

## Running the Game

```bash
git clone --recurse-submodules https://github.com/umutcanekinci/artifical-chaos.git
cd artifical-chaos
uv sync
uv run python __main__.py
```

If you forgot `--recurse-submodules`: `git submodule update --init`.

## Testing

```bash
uv run --group dev pytest tests/ -q                      # this app's own logic tests
uv run --group dev pytest tests/ --cov --cov-report=term  # with coverage
cd src/pygame_core && uv run --group dev pytest -q        # the vendored engine's own suite
uv run python scripts/smoke_test.py                       # headless boot check
```

`.github/workflows/ci.yml` runs all three (`engine-tests`, `app-tests`, `app-smoke-test`) on every push/PR, and auto-commits `.github/badges/coverage.json` (read by the README badge) after pushes to `main`.

## Architecture

### Entry point → Game class

`__main__.py` inserts `src/` and `src/pygame_core/` onto `sys.path`, then calls `Game().run()`. Unlike some sibling projects, this one does **not** `chdir` to a resource root first — it assumes cwd is the repo root (matches how `pyproject.toml`'s `pythonpath` config and CI both invoke it).

`Game` (`src/app/game.py`) extends `pygame_core.Application` directly — no panel/scene system, no YAML config. `util/constants.py` holds plain Python constants (window size, sprite scale, tuning numbers) in place of the `config/settings.yaml` pattern used by chokepoint/highrise/standoff.

### Subsystems wired in `Game.__init__`

| Object | Class | Responsibility |
|--------|-------|----------------|
| `all_sprites` / `walls` / `flags` / `soldiers` / `robots` | `GameObjectList` (plain list subclass) | Per-category entity lists; `_purge_inactive()` drops anything with `.active = False` each frame |
| `map` | `Map(TiledMap)` (`gameplay/map.py`) | Loads `assets/images/tileset/tiledmap.tmx`, pre-renders tile layers scaled by `SCALE_FACTOR`, and spawns `Flag`/`Drone`/`Soldier`/`Obstacle` from the Tiled object layer's `name` field (`"flag"`, `"spawnPoint"`, `"wall"`) — each `"flag"` object spawns one drone and one soldier, round-robining through `DRONE_CLASSES`/`SOLDIER_CLASSES` for variety |
| `camera` | `FollowCamera(pygame_core.Camera)` (`gameplay/camera.py`) | Adds `follow(target_center)` on top of the base edge-scroll/zoom camera — centers the target every frame, then clamps to map bounds |
| `player` | `Player` (`gameplay/player.py`) | The Squad Leader — see below |

`Game.update()` sets `self.delta_time` from the clock, calls `camera.follow(player position)`, updates every sprite, then purges inactive ones. `self.keys` (used by `Player.walk()`/`Soldier.walk()`) is populated once per frame by `Application._listen_inputs()` — code that constructs `Player`/`Soldier` directly (e.g. tests) must supply a `game.keys` dict-like object itself; see `tests/conftest.py`'s `FakeGame`.

### Entities

- **Player** (`gameplay/player.py`): 8-directional movement with friction (`walk()` sets `acceleration`/`rotation` from `game.keys`, `move()` applies velocity + friction + AABB collision against `walls`), footprint trail (`Footprint`, spawned on a timer, grows then expires), recruits `Soldier`s within 50px (`get_soldier()`), rank counter with an insignia sprite (`rank_up()` — cosmetic only right now). Fights with a sidearm: `shoot()` fires at the nearest drone in `game.robots` within `PLAYER_FIRE_RANGE` while the left mouse button is held, gated by `PLAYER_FIRE_COOLDOWN_MS`; `aim_at_mouse()` turns `facing` to face the cursor (cosmetic — hit resolution is range-based, not directional). `die()` (HP reaches 0, called by whatever damages the player) sets `is_dead`, zeroes velocity/acceleration, and plays the death clip; `update()` short-circuits once dead so the frozen death pose stays on screen instead of `self.active = False` removing the sprite.
- **Soldier** (`gameplay/soldier.py`): takes a `soldier_class` string (default `"Assault-Class"`) that looks up `speed`/`fire_range`/`fire_damage`/`fire_cooldown_ms` from `SOLDIER_CLASSES` (`util/constants.py`) and picks the matching sprite sheet — `Sniper-Class`, `MachineGunner-Class`, and `AntiTank-Class` are wired up the same way as `Assault-Class`, just with different stat blocks (long-range/high-damage, short-range/fast-cooldown, and high-damage/slow, respectively); `Grenadier-Class`/`RadioOperator-Class` are asset-only, blocked on mechanics (AoE, a support ability) this codebase doesn't have. Idle until `add_to_army()` is called (by `Player.get_soldier()`); once recruited, `engage()` runs each frame instead of a plain follow — it fires at the nearest drone in `game.robots` within `self.fire_range` (gated by `self.fire_cooldown_ms`) if one exists, otherwise falls back to the original chase-the-player-past-100px / hold-position behavior, and always separates from other soldiers within `AVOID_RADIUS` (`avoid_entities()`).
- **Drone / Scarab / Spider / Hornet / Wasp** (`gameplay/robot.py`): `Drone` is the shared base class, taking a `drone_type` string that looks up stats (`hp`/`speed`/`melee_range`/`fire_range`/`melee_damage`/`fire_damage`/`melee_cooldown_ms`/`fire_cooldown_ms`) **and sheet layout** (`sprite_size`/`clip_rows`/`destroyed_row`) from `DRONE_TYPES` (`util/constants.py`) and picks the matching sprite sheet; the four concrete classes are thin subclasses that just pin `drone_type`, and `DRONE_CLASSES` is the spawn-time lookup `map.py` uses. All run the same combat state machine each frame (`engage()`): idle until the player or an in-army soldier is within `AGGRO_RADIUS` (shared across types; `get_target()`, nearest-wins via `combat.find_nearest` — will chase a closer soldier over a farther player), then approaches; within `self.fire_range` it fires, within the tighter `self.melee_range` it melees instead, each gated by its own cooldown. Scarab/Spider share an 80×80 (5×5 @16px) idle/walk/fire/melee/destroyed sheet layout (Spider tuned as a melee-preferring flanker: higher speed, much shorter `fire_range`). Hornet's sheet is actually 24×24 frames in an 8×2 grid (confirmed by rendering it with a grid overlay, since the layout isn't documented in the asset pack's info file) — `clip_rows` points `idle`/`walking` at row 0 (neutral hover) and `fire`/`melee` at row 1 (firing hover); `melee_range: 0` means the melee branch in `engage()` never fires (`distance <= 0` essentially never happens), so it's ranged-only by construction rather than by special-cased logic. Wasp is 16×16, a single row — every `clip_rows` entry points at row 0, so all four statuses render identically (verified in `test_robot.py`). Neither Hornet nor Wasp has a destroyed frame (`destroyed_row: None`), so `has_destroyed_clip` is `False` for them and `die()` sets `self.active = False` immediately instead of holding a destroyed pose — `update()`/`die()` both guard on `self.active` so a drone deactivated mid-frame (e.g. by an attacker whose `update()` ran earlier the same frame) doesn't keep acting until `Game._purge_inactive()` removes it. Centipede isn't wired up — its sheet looks like a modular/segmented body (many more rows than a simple animation grid), a bigger job than adding a `DRONE_TYPES` entry (see GDD.md).
- **Flag** (`gameplay/flag.py`): pulses a separate animation loop (`draw_pulse`, not part of the normal `Animator`/update cycle since it's drawn directly by `Game.draw()`); no gameplay effect on proximity yet.
- **Obstacle** (`gameplay/map.py`): invisible `Transform`-only collision walls spawned from the Tiled map's `"wall"` objects.

### Combat (`gameplay/combat.py`)

Shared hitscan primitives used identically by `Drone.attack()`, `Player.shoot()`/`attack()`, and `Soldier.engage()`/`attack()` — deliberately kept as small near-duplicate `attack()` methods on each attacker rather than a shared base-class method, matching this codebase's existing precedent of duplicating `move()` across `Player`/`Soldier` rather than unifying it.

- `find_nearest(origin, candidates, max_range)` — the *only* targeting primitive in the game: returns the closest candidate (must expose `.position`; anything with `.active is False` is skipped) within `max_range`, or `None`. "Hitscan" here means this instant nearest-in-range check, **not** a directional raycast — facing/aim is cosmetic everywhere it's used.
- `ready_to_attack(now, last_attack_time, cooldown_ms)` — cooldown gate; `now - last_attack_time >= cooldown_ms`.
- `apply_damage(target, amount)` — decrements `target.hp`, returns whether that killed it (`hp <= 0`), so callers can trigger `target.die()`.

Per-attacker tuning lives in `util/constants.py`: `AGGRO_RADIUS`/`DESTROYED_DURATION_MS` are shared by all drones, but `hp`/`speed`/ranges/damage/cooldowns are per-drone-type in the `DRONE_TYPES` dict and per-soldier-class in the `SOLDIER_CLASSES` dict (stored on each instance in `__init__`, not read as module-level globals inside `engage()`/`attack()`); `PLAYER_FIRE_*` stays a flat module-level constant since there's only one player. First-pass numbers, not balanced (see GDD.md).

### Effects (`gameplay/effects.py`)

Purely cosmetic — spawned directly from each attacker's own `attack()`/`die()` (`Player`, `Soldier`, `Drone`), never from `gameplay/combat.py` itself, so combat's pure functions stay testable without a real `Animator`/`SpriteRenderer2D`/display surface. `assets/Effects/`/`assets/Projectiles/` have no frame-layout docs (unlike the robot/soldier sheets) — every sheet size/frame-count used here was confirmed the same way as Hornet/Wasp: render it with a grid overlay and inspect it.

- `TimedEffect(GameObject)` — shared base for one-shot sprite-sheet animations: plays a non-looping clip once and sets `self.active = False` once `Animator.is_playing` goes False. `MuzzleFlash`/`HitSpark`/`HitSpatter`/`Explosion` are thin subclasses pinning a sheet/row/frame_count/fps. Unlike the 1-frame `destroyed` clip drones use, these clips have several frames (4–9) and take real time to play through, so gating removal on `is_playing` works cleanly — no separate duration constant needed (contrast `DESTROYED_DURATION_MS`, which exists specifically because a 1-frame clip's `is_playing` goes false almost instantly).
- `Tracer(GameObject)` — not sheet-animated; lerps `rect.center` from an attacker's position to a target's over `TRACER_DURATION_MS` using a single static frame (`bullets+plasma.png` frame 0), then deactivates. A visual-only "bullet": since hits are already-instant hitscan (see Combat above), damage is applied before the Tracer even spawns — it never gates anything, purely reads as a shot crossing the screen.
- Wiring: `Player.attack()`/`Soldier.attack()` (always ranged) spawn `MuzzleFlash` + `Tracer` + `HitSpark` (their targets are always drones). `Drone.attack()` spawns `HitSpatter` always (its targets are always the player/a soldier), but only adds `MuzzleFlash`/`Tracer` when `self.status == "fire"` — melee has no gun to flash and nothing that should visibly fly across the map. `Drone.die()` spawns an `Explosion` for all four drone types, which incidentally covers Hornet/Wasp's missing destroyed-frame gap with a burst instead.
- `gameplay/animation.py`'s `add_death_clip` was generalized into `add_oneshot_clip(obj, path, row, frame_count=1, ...)` (frame_count defaults to 1, preserving the old one-frame behavior for `Drone`'s destroyed clip) so effects.py could reuse it for multi-frame one-shot clips instead of duplicating the clip-building logic.

### Win / lose (`app/game.py`)

`Game._check_end_conditions()` runs every frame from `update()` (which itself short-circuits entirely once `game_over` is set, freezing the sim). It latches `self._robots_ever_present = True` the first frame any drone exists, so an empty `game.robots` list at startup can't be mistaken for a victory; once latched, an empty list means VICTORY. `self.player.is_dead` is checked first and wins any simultaneous-frame tie, ending the run as GAME OVER instead. `draw()` calls `_draw_end_message()` when `game_over` is set, which blits a translucent overlay plus the centered end-state text over the final frame — there's no separate end-screen panel/scene, just an overlay on top of whatever was on screen.

### Collision

`gameplay/collision.py`'s `collide(mover, direction, walls)` is a single-axis AABB push-out: called once for `'x'` and once for `'y'` per moving entity per frame (see `Player.move()` / `Soldier.move()`). Resolves against the first overlapping wall only (not all of them), zeroes the corresponding velocity axis, and nudges the mover's `hit_rect` edge 0.1px past the wall's edge. `hit_rect` is a separate, smaller `pygame.Rect` from the sprite's visual `rect` — collision uses the former, rendering the latter.

### Animation

`gameplay/animation.py` has the shared helpers every entity's `__init__` calls: `add_directional_clips(obj, sheet_path, {"clip_name": row, ...})` slices frames from a sprite sheet and registers both a right-facing clip (`"{name}_0"`) and a horizontally-flipped left-facing clip (`"{name}_1"`) on the object's `Animator` component. Entities play `f"{self.status}_{self.facing}"` each update — `facing` is 0 (right) or 1 (left), never re-derived from velocity direction (it's set directly in each entity's `walk()`).

### Assets

No `AssetManager`/manifest — `ImagePath(name, folder)` (from `pygame_core.asset_path`) builds `assets/images/{folder}/{name}.png` directly; sprite sheets are loaded straight off disk via `pygame_core.sprite_sheet.SpriteSheet.from_path`. See [ASSETS.md](ASSETS.md) for the source/license of the bundled art (mattwalkden's Free Robot Warfare Pack — commercial-use-safe, unlike some of this developer's other early projects).

`assets/Effects/` and `assets/Projectiles/` sit directly under `assets/`, **not** under `assets/images/` — `ImagePath` doesn't reach them (it hardcodes `base="assets/images"`), so `gameplay/effects.py` uses the plain `AssetPath(name, folder)` (also from `pygame_core.asset_path`, `base="assets"`) instead.

Asset folders/files that exist but aren't wired into any code yet: most of `assets/Effects/` (`laser-flash`, `big-explosion`, `big-fragments`, `small-fragments`, `smoke`, `bullet-impacts` — see GDD.md's Effects & projectiles section for what each would need), `assets/Projectiles/Grenade.png`/`RPG-round.png` (no AoE weapon exists yet), 2 of the 6 soldier classes in `assets/images/soliders/` (Grenadier, RadioOperator — blocked on mechanics, not just stats), and Centipede in `assets/images/robots/` (blocked on designing a segmented-body rendering approach). See GDD.md's content-inventory table.

### pygame_core — shared submodule

`src/pygame_core/` is a git submodule (`https://github.com/umutcanekinci/pygame-core.git`), shared with chokepoint/highrise/hunted/standoff. Bump it deliberately and re-run the full test suite + smoke test after — an earlier bump was 42 commits stale and broke on Python 3.12 (a `Transform` self-referencing type hint needed `from __future__ import annotations`, only worked locally by accident because that machine's Python 3.14 defers annotation evaluation by default).

### Persistence

None yet. No save/load, no `SaveStore` usage (unlike chokepoint). `/saves/` is gitignored proactively in case this gets added later.

### What's missing relative to the sibling projects

No `config/*.yaml` (plain constants instead — see above), no `AssetManager`, no panel/UI system. Combat, a first pass of effects, and a v1 win/lose condition now exist (see Combat / Effects / Win-lose above), but the end screen is a bare text overlay, not a real panel, and 4 of 6 soldier classes and 4 of 5 drone types are wired up (see GDD.md's content-inventory table and suggested build order for what's next).
