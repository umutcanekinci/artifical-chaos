from collections import defaultdict
from types import SimpleNamespace

import pygame
import pytest
from pygame.math import Vector2

from gameplay.soldier import Soldier
from util.constants import AVOID_RADIUS, FACING_DEADZONE, SOLDIER_CLASSES

ASSAULT = SOLDIER_CLASSES["Assault-Class"]
SNIPER = SOLDIER_CLASSES["Sniper-Class"]


def press(game, *keys) -> None:
    game.keys = defaultdict(bool, {k: True for k in keys})


def test_walk_faces_left_on_a_or_left_arrow(game):
    game.player = SimpleNamespace(position=Vector2(0, 0))
    s = Soldier(game, (0, 0))
    press(game, pygame.K_a)

    s.walk()

    assert s.facing == 1


def test_walk_faces_right_on_d_or_right_arrow(game):
    game.player = SimpleNamespace(position=Vector2(0, 0))
    s = Soldier(game, (0, 0))
    s.facing = 1
    press(game, pygame.K_d)

    s.walk()

    assert s.facing == 0


def test_walk_chases_the_player_when_far_enough_away(game):
    game.player = SimpleNamespace(position=Vector2(200, 0))
    s = Soldier(game, (0, 0))  # distance 200 > 100

    s.walk()

    assert s.status == "walking"
    assert s.acceleration.length() == pytest.approx(s.ms)
    assert s.acceleration.x > 0  # player is to the right


def test_walk_stays_idle_within_the_hold_distance(game):
    game.player = SimpleNamespace(position=Vector2(50, 0))
    s = Soldier(game, (0, 0))  # distance 50 <= 100

    s.walk()

    assert s.status == "idle"
    assert s.acceleration == Vector2(0, 0)


def test_add_to_army_sets_the_flag(game):
    game.player = SimpleNamespace(position=Vector2(0, 0))
    s = Soldier(game, (0, 0))
    assert s.is_in_army is False

    s.add_to_army()

    assert s.is_in_army is True


def test_update_does_nothing_when_not_in_army(game):
    game.player = SimpleNamespace(position=Vector2(500, 0))
    s = Soldier(game, (0, 0))
    start_position = Vector2(s.position)

    s.update()

    assert s.position == start_position
    assert s.status == "idle"


def test_avoid_entities_pushes_away_from_nearby_soldiers(game):
    game.player = SimpleNamespace(position=Vector2(0, 0))
    a = Soldier(game, (0, 0))
    b = Soldier(game, (10, 0))  # distance 10 < AVOID_RADIUS

    a.acceleration = Vector2(0, 0)
    a.avoid_entities()

    # a is to the left of b, so it gets pushed further left (negative x).
    assert a.acceleration.x < 0


def test_avoid_entities_ignores_soldiers_outside_the_radius(game):
    game.player = SimpleNamespace(position=Vector2(0, 0))
    a = Soldier(game, (0, 0))
    Soldier(game, (AVOID_RADIUS + 10, 0))  # outside the avoid radius

    a.acceleration = Vector2(0, 0)
    a.avoid_entities()

    assert a.acceleration == Vector2(0, 0)


def test_avoid_entities_does_not_push_against_itself(game):
    game.player = SimpleNamespace(position=Vector2(0, 0))
    a = Soldier(game, (0, 0))

    a.acceleration = Vector2(0, 0)
    a.avoid_entities()  # only `a` exists in game.soldiers -- must not self-push

    assert a.acceleration == Vector2(0, 0)


def test_engage_fires_at_the_nearest_drone_in_range(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0))
    s = Soldier(game, (0, 0))
    drone = SimpleNamespace(position=Vector2(50, 0), active=True, hp=40)
    game.robots.append(drone)

    fake_ticks["t"] = ASSAULT["fire_cooldown_ms"]
    s.engage()

    assert s.status == "fire"
    assert s.acceleration == Vector2(0, 0)
    assert drone.hp == 40 - ASSAULT["fire_damage"]
    assert s.facing == 0  # drone is to the right

    from gameplay.effects import HitSpark, MuzzleFlash, Tracer
    kinds = [type(o) for o in game.all_sprites]
    assert MuzzleFlash in kinds
    assert Tracer in kinds
    assert HitSpark in kinds


def test_engage_falls_back_to_following_the_player_with_no_drone_in_range(game):
    game.player = SimpleNamespace(position=Vector2(200, 0))
    s = Soldier(game, (0, 0))

    s.engage()

    assert s.status == "walking"  # same as a direct walk() call, see test_walk_chases_...


def test_engage_ignores_drones_beyond_fire_range(game):
    game.player = SimpleNamespace(position=Vector2(0, 0))
    s = Soldier(game, (0, 0))
    far_drone = SimpleNamespace(position=Vector2(ASSAULT["fire_range"] + 10, 0), active=True, hp=40)
    game.robots.append(far_drone)

    s.engage()

    assert far_drone.hp == 40
    assert s.status == "idle"  # falls back to walk(); player is within hold distance


def test_engage_respects_the_fire_cooldown(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0))
    s = Soldier(game, (0, 0))
    drone = SimpleNamespace(position=Vector2(50, 0), active=True, hp=40)
    game.robots.append(drone)

    fake_ticks["t"] = ASSAULT["fire_cooldown_ms"]
    s.engage()
    assert drone.hp == 40 - ASSAULT["fire_damage"]

    fake_ticks["t"] = ASSAULT["fire_cooldown_ms"] + 1
    s.engage()

    assert drone.hp == 40 - ASSAULT["fire_damage"]  # still on cooldown


def test_engage_facing_does_not_flip_while_crossing_directly_over_a_drone(game):
    # Regression test: see FACING_DEADZONE in util/constants.py -- delta.x
    # hovering near 0 used to flip self.facing every frame from ordinary
    # movement noise while crossing to the other side of a target.
    game.player = SimpleNamespace(position=Vector2(200, 0))
    s = Soldier(game, (0, 0))
    s.facing = 0
    drone = SimpleNamespace(position=Vector2(FACING_DEADZONE - 1, 100), active=True, hp=40)
    game.robots.append(drone)

    s.engage()

    assert s.facing == 0  # unchanged -- well within the deadzone


def test_soldier_defaults_to_assault_class_stats(game):
    game.player = SimpleNamespace(position=Vector2(0, 0))
    s = Soldier(game, (0, 0))

    assert s.ms == ASSAULT["speed"]
    assert s.fire_range == ASSAULT["fire_range"]
    assert s.fire_damage == ASSAULT["fire_damage"]
    assert s.fire_cooldown_ms == ASSAULT["fire_cooldown_ms"]


def test_soldier_class_param_picks_the_matching_stats(game):
    game.player = SimpleNamespace(position=Vector2(0, 0))
    s = Soldier(game, (0, 0), soldier_class="Sniper-Class")

    assert s.ms == SNIPER["speed"]
    assert s.fire_range == SNIPER["fire_range"]
    assert s.fire_damage == SNIPER["fire_damage"]
    assert s.fire_cooldown_ms == SNIPER["fire_cooldown_ms"]


def test_sniper_fires_at_a_target_beyond_the_assault_fire_range(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0))
    s = Soldier(game, (0, 0), soldier_class="Sniper-Class")
    drone = SimpleNamespace(
        position=Vector2(ASSAULT["fire_range"] + 50, 0), active=True, hp=100,
    )
    game.robots.append(drone)

    fake_ticks["t"] = SNIPER["fire_cooldown_ms"]
    s.engage()

    assert s.status == "fire"
    assert drone.hp == 100 - SNIPER["fire_damage"]


class FakeCamera:
    def world_to_screen(self, pos):
        return Vector2(pos)

    def scaled(self, value):
        return value

    def scale_image(self, image):
        return image


def test_draw_health_does_not_error_when_full_or_damaged(game):
    game.player = SimpleNamespace(position=Vector2(0, 0))
    s = Soldier(game, (0, 0))
    surface = pygame.Surface((100, 100))

    s.draw_health(surface, FakeCamera())  # full hp -- no-op, must not raise

    s.hp = 40
    s.draw_health(surface, FakeCamera())  # damaged -- draws, must not raise


def test_draw_recruited_marker_is_a_noop_when_not_in_army(game):
    game.player = SimpleNamespace(position=Vector2(0, 0))
    s = Soldier(game, (0, 0))
    surface = pygame.Surface((100, 100))
    surface.fill((5, 5, 5))

    s.draw_recruited_marker(surface, FakeCamera())

    assert surface.get_at((50, 50))[:3] == (5, 5, 5)  # untouched


def test_draw_recruited_marker_draws_once_recruited(game):
    game.player = SimpleNamespace(position=Vector2(0, 0))
    s = Soldier(game, (0, 0))
    s.add_to_army()
    surface = pygame.Surface((100, 100))
    surface.fill((5, 5, 5))

    s.draw_recruited_marker(surface, FakeCamera())  # must not raise
