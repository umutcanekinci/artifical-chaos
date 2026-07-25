from pygame.math import Vector2

from gameplay.robot import Scarab
from util.constants import (
    AGGRO_RADIUS, DESTROYED_DURATION_MS, FIRE_COOLDOWN_MS, FIRE_RANGE,
    MELEE_COOLDOWN_MS, MELEE_RANGE, SCARAB_HP,
)


def make_scarab(game, x=0, y=0) -> Scarab:
    return Scarab(game, (x, y))


def test_spawns_idle_with_full_hp(game):
    game.player.position = Vector2(9999, 9999)  # far away -- nothing to aggro onto
    s = make_scarab(game)

    s.engage()

    assert s.hp == SCARAB_HP
    assert s.status == "idle"
    assert s.acceleration == Vector2(0, 0)


def test_ignores_targets_outside_aggro_radius(game):
    game.player.position = Vector2(AGGRO_RADIUS + 50, 0)
    s = make_scarab(game)

    assert s.get_target() is None


def test_chases_the_player_within_aggro_but_outside_fire_range(game):
    game.player.position = Vector2(FIRE_RANGE + 50, 0)
    s = make_scarab(game)

    s.engage()

    assert s.status == "walking"
    assert s.acceleration.length() > 0
    assert s.facing == 0  # target is to the right


def test_fires_when_in_fire_range_but_outside_melee_range(game, fake_ticks):
    game.player.position = Vector2(FIRE_RANGE - 10, 0)
    game.player.hp = 100
    s = make_scarab(game)

    fake_ticks["t"] = FIRE_COOLDOWN_MS  # past the initial cooldown
    s.engage()

    assert s.status == "fire"
    assert s.acceleration == Vector2(0, 0)
    assert game.player.hp < 100


def test_melees_within_melee_range(game, fake_ticks):
    game.player.position = Vector2(MELEE_RANGE - 5, 0)
    game.player.hp = 100
    s = make_scarab(game)

    fake_ticks["t"] = MELEE_COOLDOWN_MS
    s.engage()

    assert s.status == "melee"
    assert game.player.hp == 100 - 10  # MELEE_DAMAGE, see util/constants.py


def test_prefers_the_nearer_soldier_over_a_farther_player(game):
    from gameplay.soldier import Soldier

    game.player.position = Vector2(300, 0)
    soldier = Soldier(game, (50, 0))
    soldier.add_to_army()
    s = make_scarab(game)

    assert s.get_target() is soldier


def test_die_holds_the_destroyed_status_before_deactivating(game, fake_ticks):
    s = make_scarab(game)

    fake_ticks["t"] = 0
    s.die()
    assert s.status == "destroyed"
    assert s.active is True

    s.update()
    assert s.active is True  # not enough time has passed yet

    fake_ticks["t"] = DESTROYED_DURATION_MS
    s.update()
    assert s.active is False


def test_die_is_idempotent(game, fake_ticks):
    s = make_scarab(game)
    fake_ticks["t"] = 100
    s.die()
    first_death_time = s.death_time

    fake_ticks["t"] = 200
    s.die()  # must not reset the timer if already destroyed

    assert s.death_time == first_death_time
