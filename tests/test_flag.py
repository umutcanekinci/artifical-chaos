from types import SimpleNamespace

from pygame.math import Vector2

from gameplay.flag import Flag
from gameplay.soldier import Soldier
from util.constants import FLAG_CAPTURE_RADIUS, FLAG_CAPTURE_RATE, FLAG_CONTEST_RADIUS, FLAG_DECAY_RATE


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


def test_update_progresses_capture_while_held_and_uncontested(game):
    f = Flag(game, (0, 0))
    game.player.position = Vector2(0, 0)
    game.delta_time = 1.0

    f.update()

    assert f.progress == FLAG_CAPTURE_RATE
    assert f.captured is False


def test_update_does_not_progress_while_unheld(game):
    f = Flag(game, (0, 0))
    game.player.position = Vector2(9999, 9999)
    game.delta_time = 1.0

    f.update()

    assert f.progress == 0.0


def test_update_decays_progress_while_contested_even_if_held(game):
    f = Flag(game, (0, 0))
    f.progress = 50.0
    game.player.position = Vector2(0, 0)  # held...
    game.robots.append(SimpleNamespace(position=Vector2(0, 0), active=True))  # ...but also contested
    game.delta_time = 1.0

    f.update()

    assert f.progress == 50.0 - FLAG_DECAY_RATE


def test_progress_does_not_decay_below_zero(game):
    f = Flag(game, (0, 0))
    f.progress = 2.0
    game.robots.append(SimpleNamespace(position=Vector2(0, 0), active=True))
    game.delta_time = 1.0

    f.update()

    assert f.progress == 0.0


def test_becomes_captured_once_progress_reaches_100(game):
    f = Flag(game, (0, 0))
    f.progress = 100.0 - FLAG_CAPTURE_RATE
    game.player.position = Vector2(0, 0)
    game.delta_time = 1.0

    f.update()

    assert f.progress == 100.0
    assert f.captured is True


def test_progress_does_not_exceed_100(game):
    f = Flag(game, (0, 0))
    f.progress = 100.0 - 1
    game.player.position = Vector2(0, 0)
    game.delta_time = 1.0

    f.update()

    assert f.progress == 100.0


def test_a_captured_flag_no_longer_changes_progress(game):
    f = Flag(game, (0, 0))
    f.captured = True
    f.progress = 100.0
    game.robots.append(SimpleNamespace(position=Vector2(0, 0), active=True))  # would decay if not captured
    game.delta_time = 1.0

    f.update()

    assert f.progress == 100.0  # unchanged -- captured flags are locked in
