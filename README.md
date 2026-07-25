# Artificial Chaos

![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/umutcanekinci/artifical-chaos/main/.github/badges/coverage.json)

Artificial Chaos is a 2D top-down game prototype built with [pygame](https://www.pygame.org/). You control a squad leader who moves across a Tiled-authored map, recruits nearby soldiers into a following squad, and earns rank — with objective flags and roaming robots scattered around the world.

![Gameplay](docs/preview.gif)

> **⚠️ Status: unfinished prototype.** This is early work and is not in active development — combat, objectives, and win/lose conditions are unimplemented. It has, however, been migrated onto my shared [`pygame_core`](https://github.com/umutcanekinci/pygame-core) engine (vendored as a git submodule, like [chokepoint](https://github.com/umutcanekinci/chokepoint)): the game loop now extends `pygame_core.Application`, entities are `GameObject`s with `Transform`/`SpriteRenderer2D`/`Animator` components rendered through `pygame_core.Camera`, and asset/spritesheet handling uses `pygame_core` instead of project-local copies.

## Gameplay

Move the squad leader around the map. When you get close to a soldier, they join your army and start following you while spreading out to avoid crowding each other. Walking leaves a trail of fading footprints, and your rank insignia is shown next to the player. Objective flags pulse on the map, and robots roam the world. Combat, objectives, and win/lose conditions are not yet implemented.

### Entities

| Entity                | Sprite             | Behaviour                                                                 |
|-----------------------|--------------------|---------------------------------------------------------------------------|
| Squad Leader (player) | `SquadLeader.png`  | WASD/arrow movement with friction; leaves footprints; recruits nearby soldiers; rank insignia shown above |
| Soldier               | `Assault-Class.png`| Recruited when the player comes within range, then follows and avoids crowding |
| Scarab (robot)        | `Scarab.png`       | Roaming robot — idle animation only, AI not yet implemented               |
| Objective flag        | `objective-flag.png`| Pulsing objective marker, placed from the Tiled map                      |

### Controls

| Action               | Input                  |
|----------------------|------------------------|
| Move                 | `W` `A` `S` `D` / Arrow keys |
| Toggle debug overlay | `F1`                   |
| Toggle fullscreen    | `F11`                  |
| Quit                 | `Esc`                  |

## Requirements

- Python 3.10+
- [pygame](https://www.pygame.org/), [pytmx](https://github.com/bitcraft/pytmx)

## Running

```bash
git clone --recurse-submodules https://github.com/umutcanekinci/artifical-chaos.git
cd artifical-chaos
pip install pygame pytmx
python __main__.py
```

If you forgot `--recurse-submodules`: `git submodule update --init` (pulls in the `pygame_core` engine).

## Project layout

```
__main__.py               Entry point — injects src/ + src/pygame_core/ onto sys.path, runs Game()
src/app/game.py           Game (extends pygame_core.Application) — update/draw orchestration
src/gameplay/map.py       Tiled map loader + Obstacle (collision walls)
src/gameplay/camera.py    FollowCamera — pygame_core.Camera plus a follow() helper
src/gameplay/collision.py AABB Collide resolution against the wall list
src/gameplay/animation.py Builds Animator clips from pygame_core.SpriteSheet frames
src/gameplay/player.py    Player (squad leader) + Footprint
src/gameplay/soldier.py   Recruitable soldiers that follow the player
src/gameplay/robot.py     Scarab roaming robots
src/gameplay/flag.py      Objective flags (animated + pulsing marker)
src/util/constants.py     Constants (FPS, render size, sprite sizes, durations, ranks)
src/pygame_core/          Shared engine (git submodule)
assets/                   Images (soldiers, robots, UI), tileset + Tiled map
```

## Credits

Art from [mattwalkden](https://mattwalkden.itch.io/) — released into the public domain under [CC0](https://creativecommons.org/publicdomain/zero/1.0/). A written credit is not required but appreciated.

## Contributing

1. Fork this repository.
2. Clone your fork: `git clone https://github.com/<you>/artifical-chaos.git`
3. Create a branch: `git checkout -b feature/<your-feature>`
4. Commit + push: `git commit -am "<message>" && git push origin feature/<your-feature>`
5. Open a pull request.

## Author

Umutcan Ekinci — [umutcannekinci@gmail.com](mailto:umutcannekinci@gmail.com)

## License

See [LICENSE](LICENSE) (MIT).
