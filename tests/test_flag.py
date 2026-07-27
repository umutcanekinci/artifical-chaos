from types import SimpleNamespace

from pygame.math import Vector2

from gameplay.flag import Flag
from gameplay.soldier import Soldier
from util.constants import (
    FLAG_CAPTURE_RADIUS, FLAG_CAPTURE_RATE, FLAG_CONTEST_RADIUS, FLAG_DECAY_RATE,
    FLAG_SPAWN_COOLDOWN_MS, FLAG_SPAWN_MAX_CONCURRENT, FLAG_SPAWN_RADIUS,
)


def test_spawns_uncaptured_with_zero_progress(game):
    f = Flag(game, (0, 0))

    assert f.progress == 0.0
    assert f.captured is False


def test_is_held_when_the_player_is_within_capture_radius(game):
    f = Flag(game, (0, 0))
    game.player.position = Vector2(FLAG_CAPTURE_RADIUS - 10, 0)

    assert f.is_held() is True


def test_is_not_held_when_the_player_is_outside_capture_radius(game):
    f = Flag(game, (0, 0))
    game.player.position = Vector2(FLAG_CAPTURE_RADIUS + 10, 0)

    assert f.is_held() is False


def test_is_held_by_an_in_army_soldier_too(game):
    f = Flag(game, (0, 0))
    game.player.position = Vector2(9999, 9999)  # far away -- doesn't hold it
    s = Soldier(game, (10, 0))
    s.add_to_army()

    assert f.is_held() is True


def test_a_soldier_not_in_the_army_does_not_count_as_a_holder(game):
    f = Flag(game, (0, 0))
    game.player.position = Vector2(9999, 9999)
    Soldier(game, (10, 0))  # never recruited

    assert f.is_held() is False


def test_is_contested_when_a_drone_is_within_contest_radius(game):
    f = Flag(game, (0, 0))
    game.robots.append(SimpleNamespace(position=Vector2(FLAG_CONTEST_RADIUS - 10, 0), active=True))

    assert f.is_contested() is True


def test_is_not_contested_when_no_drone_is_within_contest_radius(game):
    f = Flag(game, (0, 0))
    game.robots.append(SimpleNamespace(position=Vector2(FLAG_CONTEST_RADIUS + 10, 0), active=True))

    assert f.is_contested() is False


def test_update_progresses_capture_while_held_and_uncontested(game, fake_ticks):
    f = Flag(game, (0, 0))
    game.player.position = Vector2(0, 0)
    game.delta_time = 1.0

    f.update()

    assert f.progress == FLAG_CAPTURE_RATE
    assert f.captured is False


def test_update_does_not_progress_while_unheld(game, fake_ticks):
    f = Flag(game, (0, 0))
    game.player.position = Vector2(9999, 9999)
    game.delta_time = 1.0

    f.update()

    assert f.progress == 0.0


def test_update_decays_progress_while_contested_even_if_held(game, fake_ticks):
    f = Flag(game, (0, 0))
    f.progress = 50.0
    game.player.position = Vector2(0, 0)  # held...
    game.robots.append(SimpleNamespace(position=Vector2(0, 0), active=True))  # ...but also contested
    game.delta_time = 1.0

    f.update()

    assert f.progress == 50.0 - FLAG_DECAY_RATE


def test_progress_does_not_decay_below_zero(game, fake_ticks):
    f = Flag(game, (0, 0))
    f.progress = 2.0
    game.robots.append(SimpleNamespace(position=Vector2(0, 0), active=True))
    game.delta_time = 1.0

    f.update()

    assert f.progress == 0.0


def test_becomes_captured_once_progress_reaches_100(game, fake_ticks):
    f = Flag(game, (0, 0))
    f.progress = 100.0 - FLAG_CAPTURE_RATE
    game.player.position = Vector2(0, 0)
    game.delta_time = 1.0

    f.update()

    assert f.progress == 100.0
    assert f.captured is True


def test_becoming_captured_triggers_player_rank_up(game, fake_ticks):
    rank_ups = []
    game.player.rank_up = lambda: rank_ups.append(1)
    f = Flag(game, (0, 0))
    f.progress = 100.0 - FLAG_CAPTURE_RATE
    game.player.position = Vector2(0, 0)
    game.delta_time = 1.0

    f.update()

    assert len(rank_ups) == 1


def test_progress_does_not_exceed_100(game, fake_ticks):
    f = Flag(game, (0, 0))
    f.progress = 100.0 - 1
    game.player.position = Vector2(0, 0)
    game.delta_time = 1.0

    f.update()

    assert f.progress == 100.0


def test_a_captured_flag_no_longer_changes_progress(game, fake_ticks):
    f = Flag(game, (0, 0))
    f.captured = True
    f.progress = 100.0
    game.robots.append(SimpleNamespace(position=Vector2(0, 0), active=True))  # would decay if not captured
    game.delta_time = 1.0

    f.update()

    assert f.progress == 100.0  # unchanged -- captured flags are locked in


def test_an_already_captured_flag_does_not_rank_up_again(game, fake_ticks):
    rank_ups = []
    game.player.rank_up = lambda: rank_ups.append(1)
    f = Flag(game, (0, 0))
    f.captured = True
    f.progress = 100.0
    game.player.position = Vector2(0, 0)
    game.delta_time = 1.0

    f.update()

    assert len(rank_ups) == 0


def test_spawn_drone_does_nothing_before_its_cooldown_elapses(game, fake_ticks):
    f = Flag(game, (0, 0))

    fake_ticks["t"] = FLAG_SPAWN_COOLDOWN_MS - 1
    f._spawn_drone()

    assert len(game.robots) == 0
    assert f.spawned_drones == []


def test_spawn_drone_spawns_near_the_flag_once_its_cooldown_elapses(game, fake_ticks):
    f = Flag(game, (0, 0))

    fake_ticks["t"] = FLAG_SPAWN_COOLDOWN_MS
    f._spawn_drone()

    assert len(game.robots) == 1
    assert len(f.spawned_drones) == 1
    drone = game.robots[0]
    assert (Vector2(drone.position) - Vector2(f.rect.center)).length() <= FLAG_SPAWN_RADIUS


def test_spawn_drone_respects_its_own_cooldown(game, fake_ticks):
    f = Flag(game, (0, 0))

    fake_ticks["t"] = FLAG_SPAWN_COOLDOWN_MS
    f._spawn_drone()
    fake_ticks["t"] += 1  # nowhere near the next cooldown
    f._spawn_drone()

    assert len(game.robots) == 1  # still just the first one


def test_spawn_drone_caps_concurrent_count(game, fake_ticks):
    f = Flag(game, (0, 0))

    for i in range(FLAG_SPAWN_MAX_CONCURRENT + 3):
        fake_ticks["t"] = (i + 1) * FLAG_SPAWN_COOLDOWN_MS
        f._spawn_drone()

    assert len(game.robots) == FLAG_SPAWN_MAX_CONCURRENT
    assert len(f.spawned_drones) == FLAG_SPAWN_MAX_CONCURRENT


def test_spawn_drone_allows_more_once_a_previous_one_dies(game, fake_ticks):
    f = Flag(game, (0, 0))

    for i in range(FLAG_SPAWN_MAX_CONCURRENT):
        fake_ticks["t"] = (i + 1) * FLAG_SPAWN_COOLDOWN_MS
        f._spawn_drone()
    assert len(f.spawned_drones) == FLAG_SPAWN_MAX_CONCURRENT

    f.spawned_drones[0].active = False  # simulate one of them dying
    fake_ticks["t"] = (FLAG_SPAWN_MAX_CONCURRENT + 1) * FLAG_SPAWN_COOLDOWN_MS
    f._spawn_drone()

    assert len(game.robots) == FLAG_SPAWN_MAX_CONCURRENT + 1  # room freed up for one more
    assert len(f.spawned_drones) == FLAG_SPAWN_MAX_CONCURRENT  # the dead one was pruned out


def test_spawn_drone_never_fires_once_the_flag_is_captured(game, fake_ticks):
    f = Flag(game, (0, 0))
    f.captured = True
    f.progress = 100.0
    game.player.position = Vector2(0, 0)
    game.delta_time = 1.0

    fake_ticks["t"] = FLAG_SPAWN_COOLDOWN_MS * 3
    f.update()  # update() itself, not _spawn_drone() directly -- proves the real gate

    assert len(game.robots) == 0
