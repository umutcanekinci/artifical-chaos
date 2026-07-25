"""Headless boot check -- catches asset/map wiring mistakes that only
surface once the game is actually built and run (e.g. a Tiled object layer
referencing a renamed asset). Run locally with:

    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run python scripts/smoke_test.py

Requires cwd = repo root (matches how __main__.py and CI both invoke it).
"""
import sys

sys.path.insert(0, "src")
sys.path.insert(0, "src/pygame_core")


def boot_game() -> None:
    from app.game import Game

    game = Game()
    print(f"  map spawned: {len(game.flags)} flags, {len(game.soldiers)} soldiers, "
          f"{len(game.robots)} robots, {len(game.walls)} walls")

    # _listen_inputs() is normally called every frame by Application.run()
    # before update() -- populates game.keys, which Player/Soldier read.
    game._listen_inputs()
    for _ in range(3):
        game.update()
        game.draw()
    print("  3 update/draw frames: OK")


def main() -> None:
    print("Booting Game() and running a few frames...")
    boot_game()
    print("Smoke test passed.")


if __name__ == "__main__":
    main()
