from collections import defaultdict
from types import SimpleNamespace

import pygame
import pytest
from pygame.math import Vector2

from gameplay.player import Footprint, Player
from util.constants import FOOTPRINT_DURATION, FRICTION, PLAYER_FIRE_COOLDOWN_MS, PLAYER_FIRE_RANGE


def press(game, *keys) -> None:
    game.keys = defaultdict(bool, {k: True for k in keys})


class FakeCamera:
    """screen_to_world as an identity -- Player.aim_at_mouse() only needs
    *some* world position to compare against, not real camera math (already
    covered by tests/test_camera.py)."""
    def screen_to_world(self, pos):
        return Vector2(pos)


def make_shooting_player(game, x=0.0, y=0.0) -> Player:
    game.camera = FakeCamera()
    game.mouse = SimpleNamespace(position=(0, 0))
    return Player(game, (x, y))


def test_walk_up_sets_negative_y_rotation(game):
    p = Player(game, (0, 0))
    press(game, pygame.K_w)

    p.walk()

    assert p.rotation.y == -1
    assert p.rotation.x == 0
    assert p.status == "walking"


def test_walk_down_sets_positive_y_rotation(game):
    p = Player(game, (0, 0))
    press(game, pygame.K_s)

    p.walk()

    assert p.rotation.y == 1


def test_walk_left_sets_negative_x_rotation_and_faces_left(game):
    p = Player(game, (0, 0))
    press(game, pygame.K_a)

    p.walk()

    assert p.rotation.x == -1
    assert p.facing == 1


def test_walk_right_sets_positive_x_rotation_and_faces_right(game):
    p = Player(game, (0, 0))
    press(game, pygame.K_d)

    p.walk()

    assert p.rotation.x == 1
    assert p.facing == 0


def test_walk_with_no_keys_is_idle_with_zero_acceleration(game):
    p = Player(game, (0, 0))

    p.walk()

    assert p.status == "idle"
    assert p.acceleration == Vector2(0, 0)


def test_walk_diagonal_sets_normalized_acceleration_toward_ms(game):
    p = Player(game, (0, 0))
    press(game, pygame.K_d, pygame.K_s)  # right + down

    p.walk()

    assert p.status == "walking"
    assert p.acceleration.length() == pytest.approx(p.ms)


def count_footprints(game) -> int:
    return len([o for o in game.all_sprites if isinstance(o, Footprint)])


def test_walk_drops_a_footprint_only_after_the_spacing_interval(game, fake_ticks):
    # last_footprint starts at 0, and the gate is `now - last_footprint >=
    # FOOTPRINT_DURATION`, so nothing drops until the clock actually reaches
    # a full interval -- not immediately at t=0.
    p = Player(game, (0, 0))
    press(game, pygame.K_d)

    fake_ticks["t"] = 0
    p.walk()
    assert count_footprints(game) == 0

    fake_ticks["t"] = FOOTPRINT_DURATION - 1
    p.walk()
    assert count_footprints(game) == 0  # still too soon

    fake_ticks["t"] = FOOTPRINT_DURATION
    p.walk()
    assert count_footprints(game) == 1

    fake_ticks["t"] = FOOTPRINT_DURATION * 2
    p.walk()
    assert count_footprints(game) == 2


def test_footprints_alternate_feet(game, fake_ticks):
    p = Player(game, (0, 0))
    press(game, pygame.K_d)
    assert p.left_foot is True  # initial

    fake_ticks["t"] = FOOTPRINT_DURATION
    p.walk()
    assert p.left_foot is False  # first footprint flips it

    fake_ticks["t"] = FOOTPRINT_DURATION * 2
    p.walk()
    assert p.left_foot is True


def test_move_applies_friction_and_updates_position(game):
    p = Player(game, (0, 0))
    p.acceleration = Vector2(1, 0)
    game.delta_time = 1.0

    p.move()

    expected_velocity = Vector2(1, 0) * game.delta_time * p.ms
    expected_velocity -= expected_velocity * FRICTION
    assert p.velocity == expected_velocity
    assert p.position == Vector2(0, 0) + expected_velocity * game.delta_time


def test_get_soldier_recruits_soldiers_within_range(game):
    from gameplay.soldier import Soldier

    p = Player(game, (0, 0))
    near = Soldier(game, (30, 0))   # distance 30 < 50
    far = Soldier(game, (200, 0))   # distance 200 >= 50

    p.get_soldier()

    assert near.is_in_army is True
    assert far.is_in_army is False


def test_rank_up_increments_rank(game):
    p = Player(game, (0, 0))
    assert p.rank == 0

    p.rank_up()

    assert p.rank == 1


def test_footprint_grows_then_expires(game, fake_ticks):
    fake_ticks["t"] = 0
    fp = Footprint(game, (0, 0))
    assert fp.size == 1
    assert fp.active is True

    fp.update()
    assert fp.size == 2

    fake_ticks["t"] = FOOTPRINT_DURATION * 2
    fp.update()
    assert fp.active is False


def test_shoot_does_nothing_without_the_mouse_held(game, monkeypatch):
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (False, False, False))
    p = make_shooting_player(game)
    drone = SimpleNamespace(position=Vector2(50, 0), active=True, hp=40)
    game.robots.append(drone)

    fired = p.shoot()

    assert fired is False
    assert drone.hp == 40


def test_shoot_damages_the_nearest_drone_once_off_cooldown(game, monkeypatch, fake_ticks):
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (True, False, False))
    p = make_shooting_player(game)
    drone = SimpleNamespace(position=Vector2(50, 0), active=True, hp=40)
    game.robots.append(drone)

    fake_ticks["t"] = 0
    p.shoot()
    assert drone.hp == 40  # last_attack_time starts at 0 -- same cooldown-gate pattern as everywhere else

    fake_ticks["t"] = PLAYER_FIRE_COOLDOWN_MS
    fired = p.shoot()

    assert fired is True
    assert p.status == "fire"
    assert drone.hp == 40 - 12  # PLAYER_FIRE_DAMAGE, see util/constants.py

    from gameplay.effects import HitSpark, MuzzleFlash, Tracer
    kinds = [type(o) for o in game.all_sprites]
    assert MuzzleFlash in kinds
    assert Tracer in kinds
    assert HitSpark in kinds


def test_shoot_ignores_drones_beyond_fire_range(game, monkeypatch, fake_ticks):
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (True, False, False))
    p = make_shooting_player(game)
    drone = SimpleNamespace(position=Vector2(PLAYER_FIRE_RANGE + 10, 0), active=True, hp=40)
    game.robots.append(drone)

    fake_ticks["t"] = PLAYER_FIRE_COOLDOWN_MS
    p.shoot()

    assert drone.hp == 40


def test_aim_at_mouse_faces_left_when_mouse_is_left_of_the_player(game):
    p = make_shooting_player(game, x=100, y=0)
    game.mouse.position = (0, 0)  # world x=0 < player x=100

    p.aim_at_mouse()

    assert p.facing == 1


def test_aim_at_mouse_faces_right_when_mouse_is_right_of_the_player(game):
    p = make_shooting_player(game, x=0, y=0)
    game.mouse.position = (100, 0)

    p.aim_at_mouse()

    assert p.facing == 0


def test_die_sets_dead_flag_and_stops_movement(game):
    p = make_shooting_player(game)
    p.velocity = Vector2(5, 5)
    p.acceleration = Vector2(1, 1)

    p.die()

    assert p.is_dead is True
    assert p.status == "death"
    assert p.velocity == Vector2(0, 0)
    assert p.acceleration == Vector2(0, 0)


def test_die_is_idempotent(game):
    p = make_shooting_player(game)
    p.die()
    p.velocity = Vector2(3, 0)  # simulate something external nudging it

    p.die()  # must not reset state a second time

    assert p.velocity == Vector2(3, 0)


def test_update_does_nothing_once_dead(game, monkeypatch):
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (True, False, False))
    p = make_shooting_player(game)
    p.die()
    start_position = Vector2(p.position)
    press(game, pygame.K_d)

    p.update()

    assert p.position == start_position
    assert p.status == "death"
