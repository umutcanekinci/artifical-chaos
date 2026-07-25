from types import SimpleNamespace

from pygame.math import Vector2

from gameplay.combat import apply_damage, find_nearest, ready_to_attack


def make_entity(x, y, active=True):
    return SimpleNamespace(position=Vector2(x, y), active=active)


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
