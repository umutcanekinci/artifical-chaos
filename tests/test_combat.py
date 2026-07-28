from types import SimpleNamespace

import pygame
from pygame.math import Vector2

from gameplay.combat import (
    apply_damage, find_all_in_range, find_nearest, has_line_of_sight, muzzle_position, raycast, ready_to_attack,
)


def make_entity(x, y, active=True):
    return SimpleNamespace(position=Vector2(x, y), active=active)


def make_wall(rect: pygame.Rect):
    return SimpleNamespace(rect=rect)


def test_find_nearest_returns_the_closest_candidate_in_range():
    origin = Vector2(0, 0)
    near = make_entity(10, 0)
    far = make_entity(50, 0)

    result = find_nearest(origin, [far, near], max_range=100)

    assert result is near


def test_find_nearest_ignores_candidates_beyond_max_range():
    origin = Vector2(0, 0)
    out_of_range = make_entity(200, 0)

    result = find_nearest(origin, [out_of_range], max_range=100)

    assert result is None


def test_find_nearest_returns_none_with_no_candidates():
    assert find_nearest(Vector2(0, 0), [], max_range=100) is None


def test_find_nearest_skips_inactive_candidates():
    origin = Vector2(0, 0)
    dead = make_entity(10, 0, active=False)
    alive = make_entity(50, 0, active=True)

    result = find_nearest(origin, [dead, alive], max_range=100)

    assert result is alive


def test_find_nearest_treats_missing_active_attribute_as_alive():
    # find_nearest is used with plain objects (e.g. the real Player) that
    # don't necessarily define `.active` -- must not require it.
    origin = Vector2(0, 0)
    no_active_attr = SimpleNamespace(position=Vector2(10, 0))

    assert find_nearest(origin, [no_active_attr], max_range=100) is no_active_attr


def test_find_nearest_includes_a_candidate_exactly_at_max_range():
    origin = Vector2(0, 0)
    at_edge = make_entity(100, 0)

    assert find_nearest(origin, [at_edge], max_range=100) is at_edge


def test_find_all_in_range_returns_every_candidate_within_range():
    origin = Vector2(0, 0)
    near = make_entity(10, 0)
    also_near = make_entity(20, 0)
    far = make_entity(500, 0)

    result = find_all_in_range(origin, [near, far, also_near], max_range=100)

    assert len(result) == 2
    assert near in result and also_near in result


def test_find_all_in_range_returns_empty_list_with_no_candidates_in_range():
    assert find_all_in_range(Vector2(0, 0), [make_entity(500, 0)], max_range=100) == []


def test_find_all_in_range_skips_inactive_candidates():
    origin = Vector2(0, 0)
    dead = make_entity(10, 0, active=False)
    alive = make_entity(20, 0, active=True)

    result = find_all_in_range(origin, [dead, alive], max_range=100)

    assert result == [alive]


def test_find_all_in_range_includes_a_candidate_exactly_at_max_range():
    origin = Vector2(0, 0)
    at_edge = make_entity(100, 0)

    assert find_all_in_range(origin, [at_edge], max_range=100) == [at_edge]


def test_ready_to_attack_false_before_cooldown_elapses():
    assert ready_to_attack(now=299, last_attack_time=0, cooldown_ms=300) is False


def test_ready_to_attack_true_once_cooldown_elapses():
    assert ready_to_attack(now=300, last_attack_time=0, cooldown_ms=300) is True


def test_apply_damage_reduces_hp_and_reports_survival():
    target = SimpleNamespace(hp=40)

    killed = apply_damage(target, 10)

    assert target.hp == 30
    assert killed is False


def test_apply_damage_reports_death_at_exactly_zero_hp():
    target = SimpleNamespace(hp=10)

    killed = apply_damage(target, 10)

    assert target.hp == 0
    assert killed is True


def test_apply_damage_reports_death_when_overkilled():
    target = SimpleNamespace(hp=5)

    killed = apply_damage(target, 999)

    assert target.hp == -994
    assert killed is True


def test_raycast_returns_none_with_no_walls():
    assert raycast(Vector2(0, 0), Vector2(1, 0), max_range=100, walls=[]) is None


def test_raycast_returns_none_when_nothing_is_in_the_path():
    wall = make_wall(pygame.Rect(200, 200, 20, 20))  # well off to the side
    assert raycast(Vector2(0, 0), Vector2(1, 0), max_range=100, walls=[wall]) is None


def test_raycast_returns_none_for_a_zero_length_direction():
    wall = make_wall(pygame.Rect(50, -10, 20, 20))
    assert raycast(Vector2(0, 0), Vector2(0, 0), max_range=100, walls=[wall]) is None


def test_raycast_hits_a_wall_directly_in_the_path():
    wall = make_wall(pygame.Rect(50, -10, 20, 20))  # spans x 50-70, y -10-10

    hit = raycast(Vector2(0, 0), Vector2(1, 0), max_range=100, walls=[wall])

    assert hit is not None
    assert hit.x == 50  # entry point -- the near edge, not the far one
    assert hit.y == 0


def test_raycast_ignores_a_wall_beyond_max_range():
    wall = make_wall(pygame.Rect(500, -10, 20, 20))

    hit = raycast(Vector2(0, 0), Vector2(1, 0), max_range=100, walls=[wall])

    assert hit is None


def test_raycast_returns_the_nearest_of_several_walls_in_the_path():
    near_wall = make_wall(pygame.Rect(30, -10, 20, 20))
    far_wall = make_wall(pygame.Rect(70, -10, 20, 20))

    hit = raycast(Vector2(0, 0), Vector2(1, 0), max_range=100, walls=[far_wall, near_wall])

    assert hit.x == 30


def test_has_line_of_sight_true_with_no_walls():
    assert has_line_of_sight(Vector2(0, 0), Vector2(100, 0), walls=[]) is True


def test_has_line_of_sight_false_when_a_wall_blocks_the_path():
    wall = make_wall(pygame.Rect(50, -10, 20, 20))
    assert has_line_of_sight(Vector2(0, 0), Vector2(100, 0), walls=[wall]) is False


def test_has_line_of_sight_true_when_the_wall_is_behind_the_target():
    # The wall sits past the target, not between origin and target -- a
    # wall behind the target must never count as blocking it.
    wall = make_wall(pygame.Rect(150, -10, 20, 20))
    assert has_line_of_sight(Vector2(0, 0), Vector2(100, 0), walls=[wall]) is True


def test_has_line_of_sight_true_when_target_and_origin_coincide():
    assert has_line_of_sight(Vector2(5, 5), Vector2(5, 5), walls=[make_wall(pygame.Rect(0, 0, 1000, 1000))]) is True


def test_has_line_of_sight_false_when_a_wall_sits_exactly_at_the_target():
    # A wall whose edge lines up with the target's own position must still
    # count as blocking -- clipline() includes both endpoints.
    wall = make_wall(pygame.Rect(90, -10, 20, 20))
    assert has_line_of_sight(Vector2(0, 0), Vector2(100, 0), walls=[wall]) is False


def test_muzzle_position_offsets_right_when_facing_right():
    result = muzzle_position(Vector2(0, 0), facing=0, offset_x=12, offset_y=-6)

    assert result == Vector2(12, -6)


def test_muzzle_position_mirrors_offset_x_when_facing_left():
    result = muzzle_position(Vector2(0, 0), facing=1, offset_x=12, offset_y=-6)

    assert result == Vector2(-12, -6)


def test_muzzle_position_offset_y_does_not_mirror_with_facing():
    right = muzzle_position(Vector2(0, 0), facing=0, offset_x=12, offset_y=-6)
    left = muzzle_position(Vector2(0, 0), facing=1, offset_x=12, offset_y=-6)

    assert right.y == left.y == -6


def test_muzzle_position_is_relative_to_the_given_origin():
    result = muzzle_position(Vector2(5, 5), facing=0, offset_x=12, offset_y=-6)

    assert result == Vector2(17, -1)
