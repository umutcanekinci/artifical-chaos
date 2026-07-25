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
| `map` | `Map(TiledMap)` (`gameplay/map.py`) | Loads `assets/images/tileset/tiledmap.tmx`, pre-renders tile layers scaled by `SCALE_FACTOR`, and spawns `Flag`/`Scarab`/`Soldier`/`Obstacle` from the Tiled object layer's `name` field (`"flag"`, `"spawnPoint"`, `"wall"`) |
| `camera` | `FollowCamera(pygame_core.Camera)` (`gameplay/camera.py`) | Adds `follow(target_center)` on top of the base edge-scroll/zoom camera — centers the target every frame, then clamps to map bounds |
| `player` | `Player` (`gameplay/player.py`) | The Squad Leader — see below |

`Game.update()` sets `self.delta_time` from the clock, calls `camera.follow(player position)`, updates every sprite, then purges inactive ones. `self.keys` (used by `Player.walk()`/`Soldier.walk()`) is populated once per frame by `Application._listen_inputs()` — code that constructs `Player`/`Soldier` directly (e.g. tests) must supply a `game.keys` dict-like object itself; see `tests/conftest.py`'s `FakeGame`.

### Entities

- **Player** (`gameplay/player.py`): 8-directional movement with friction (`walk()` sets `acceleration`/`rotation` from `game.keys`, `move()` applies velocity + friction + AABB collision against `walls`), footprint trail (`Footprint`, spawned on a timer, grows then expires), recruits `Soldier`s within 50px (`get_soldier()`), rank counter with an insignia sprite (`rank_up()` — cosmetic only right now).
- **Soldier** (`gameplay/soldier.py`): idle until `add_to_army()` is called (by `Player.get_soldier()`); once recruited, chases the player when farther than 100px, holds position otherwise, and separates from other soldiers within `AVOID_RADIUS` (`avoid_entities()`). No combat.
- **Scarab** (`gameplay/robot.py`, class name `Scarab`): the only drone currently spawned. Idle animation only — no AI, no combat, no aggro.
- **Flag** (`gameplay/flag.py`): pulses a separate animation loop (`draw_pulse`, not part of the normal `Animator`/update cycle since it's drawn directly by `Game.draw()`); no gameplay effect on proximity yet.
- **Obstacle** (`gameplay/map.py`): invisible `Transform`-only collision walls spawned from the Tiled map's `"wall"` objects.

### Collision

`gameplay/collision.py`'s `collide(mover, direction, walls)` is a single-axis AABB push-out: called once for `'x'` and once for `'y'` per moving entity per frame (see `Player.move()` / `Soldier.move()`). Resolves against the first overlapping wall only (not all of them), zeroes the corresponding velocity axis, and nudges the mover's `hit_rect` edge 0.1px past the wall's edge. `hit_rect` is a separate, smaller `pygame.Rect` from the sprite's visual `rect` — collision uses the former, rendering the latter.

### Animation

`gameplay/animation.py` has the shared helpers every entity's `__init__` calls: `add_directional_clips(obj, sheet_path, {"clip_name": row, ...})` slices frames from a sprite sheet and registers both a right-facing clip (`"{name}_0"`) and a horizontally-flipped left-facing clip (`"{name}_1"`) on the object's `Animator` component. Entities play `f"{self.status}_{self.facing}"` each update — `facing` is 0 (right) or 1 (left), never re-derived from velocity direction (it's set directly in each entity's `walk()`).

### Assets

No `AssetManager`/manifest — `ImagePath(name, folder)` (from `pygame_core.asset_path`) builds `assets/images/{folder}/{name}.png` directly; sprite sheets are loaded straight off disk via `pygame_core.sprite_sheet.SpriteSheet.from_path`. See [ASSETS.md](ASSETS.md) for the source/license of the bundled art (mattwalkden's Free Robot Warfare Pack — commercial-use-safe, unlike some of this developer's other early projects).

Asset folders that exist but aren't wired into any code yet: `assets/Effects/` (explosions, muzzle flashes, hit sparks/spatters, smoke), `assets/Projectiles/` (bullets+plasma, grenade, RPG round), 5 of the 6 soldier classes in `assets/images/soliders/`, 4 of the 5 drone types in `assets/images/robots/`. See GDD.md's content-inventory table.

### pygame_core — shared submodule

`src/pygame_core/` is a git submodule (`https://github.com/umutcanekinci/pygame-core.git`), shared with chokepoint/highrise/hunted/standoff. Bump it deliberately and re-run the full test suite + smoke test after — an earlier bump was 42 commits stale and broke on Python 3.12 (a `Transform` self-referencing type hint needed `from __future__ import annotations`, only worked locally by accident because that machine's Python 3.14 defers annotation evaluation by default).

### Persistence

None yet. No save/load, no `SaveStore` usage (unlike chokepoint). `/saves/` is gitignored proactively in case this gets added later.

### What's missing relative to the sibling projects

No `config/*.yaml` (plain constants instead — see above), no `AssetManager`, no panel/UI system, no win/lose condition, no combat of any kind (see GDD.md's "not implemented" list — this is the actual current gap, not just missing polish).
