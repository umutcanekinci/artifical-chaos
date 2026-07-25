from collections import defaultdict

import pygame
import pytest
from pygame.math import Vector2

from gameplay.player import Footprint, Player
from util.constants import FOOTPRINT_DURATION, FRICTION


def press(game, *keys) -> None:
    game.keys = defaultdict(bool, {k: True for k in keys})


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
