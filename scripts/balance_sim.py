"""Headless 1v1 time-to-kill simulation: Player and every non-support Soldier
class vs every Drone type, driven through the real move()/engage()/attack()
code (not analytic dps math) so range/cooldown/kiting/melee-vs-ranged
branching all behave exactly like a real match -- used to sanity-check
DRONE_TYPES/SOLDIER_CLASSES/PLAYER_FIRE_* changes before committing to them,
same "simulate, don't just guess" discipline as GDD.md's drone-hp balance
pass. Not a pass/fail check (no assertions, no CI wiring) -- read the table
and judge whether a matchup's outcome still makes sense for that class's
GDD-stated role. Run with:

    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy uv run python scripts/balance_sim.py

Requires cwd = repo root (matches scripts/smoke_test.py's convention).

Both combatants stand at a fixed starting distance and fight to the death or
a 60-simulated-second timeout; a stationary bystander Player is always
present too (Soldier-attacker rows need one -- Drone/Soldier.engage() reads
game.player), but combat.find_nearest's `<=` tie-break means whichever
candidate is *last* in its own candidate list wins an exact-distance tie,
so a co-located Soldier (checked second, after the Player) is what actually
gets targeted -- verified by asserting the bystander Player's hp never
drops in the Soldier-attacker rows below, not just assumed.
"""
import collections
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

sys.path.insert(0, "src")
sys.path.insert(0, "src/pygamine")

import pygame
from pygame.math import Vector2

pygame.init()
pygame.display.set_mode((1, 1))

from gameplay.player import Player
from gameplay.robot import DRONE_CLASSES
from gameplay.soldier import Soldier
from util.constants import DRONE_TYPES, SOLDIER_CLASSES

FIXED_DT = 1 / 60
MAX_SIM_SECONDS = 60


class FakeGame:
    def __init__(self):
        self.all_sprites = []
        self.walls = []
        self.flags = []
        self.soldiers = []
        self.robots = []
        self.keys = collections.defaultdict(bool)
        self.delta_time = FIXED_DT
        self.mouse = type("Mouse", (), {"position": (0, 0)})()
        self.camera = type("Camera", (), {"screen_to_world": staticmethod(lambda pos: self._aim_target)})()


def run_1v1(attacker_factory, drone_type: str, start_distance: float):
    """Returns (result, seconds, defeated_attacker_hp) where result is one
    of "attacker_wins" / "drone_wins" / "timeout"."""
    game = FakeGame()
    ticks = {"t": 0}
    pygame.time.get_ticks = lambda: ticks["t"]
    pygame.mouse.get_pressed = lambda: (True, False, False)

    player = Player(game, (0, 0))
    game.player = player
    drone = DRONE_CLASSES[drone_type](game, (start_distance, 0))
    game._aim_target = drone.position

    attacker = attacker_factory(game)
    is_player_attacker = attacker is player
    if not is_player_attacker:
        attacker.add_to_army()
        attacker.position = Vector2(0, 0)
        attacker.rect.center = attacker.hit_rect.center = attacker.position

    for i in range(int(MAX_SIM_SECONDS / FIXED_DT)):
        ticks["t"] = int(i * FIXED_DT * 1000)
        game._aim_target = drone.position

        drone.engage()
        drone.move()
        if is_player_attacker:
            player.aim_at_mouse()
            player.shoot()
        else:
            attacker.engage()
            attacker.move()
            assert player.hp == 100, "bystander Player was targeted instead of the real attacker"

        if drone.hp <= 0 or not drone.active:
            return "attacker_wins", i * FIXED_DT, (player.hp if is_player_attacker else attacker.hp)
        if (player.hp if is_player_attacker else attacker.hp) <= 0:
            return "drone_wins", i * FIXED_DT, 0

    return "timeout", MAX_SIM_SECONDS, 0


def main() -> None:
    print(f"{'Drone':<10} {'Attacker':<20} {'Result':<14} {'Time (s)':>8} {'HP left':>8}")
    print("-" * 64)

    for drone_type in DRONE_TYPES:
        result, t, hp_left = run_1v1(lambda g: g.player, drone_type, DRONE_TYPES[drone_type]["fire_range"] or
                                     DRONE_TYPES[drone_type]["melee_range"] + 10)
        print(f"{drone_type:<10} {'Player':<20} {result:<14} {t:>8.2f} {hp_left:>8.0f}")

    print()
    for drone_type in DRONE_TYPES:
        for soldier_class, stats in SOLDIER_CLASSES.items():
            if stats["support_cooldown_ms"] > 0:
                continue  # RadioOperator doesn't fight
            start = stats["fire_range"] - 20
            result, t, hp_left = run_1v1(
                lambda g, sc=soldier_class: Soldier(g, (0, 0), soldier_class=sc), drone_type, start)
            print(f"{drone_type:<10} {soldier_class:<20} {result:<14} {t:>8.2f} {hp_left:>8.0f}")


if __name__ == "__main__":
    main()
