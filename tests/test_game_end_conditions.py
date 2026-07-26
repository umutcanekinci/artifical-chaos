"""Game._check_end_conditions() in isolation -- calling the real unbound
method against a lightweight stand-in avoids constructing a full Game()
(which loads the real Tiled map) for what's really a small state-machine
test."""
from types import SimpleNamespace

from app.game import Game


def make_flag(*, captured=False):
    return SimpleNamespace(captured=captured)


def make_fake_game(*, flags=None, player_is_dead=False):
    return SimpleNamespace(
        flags=flags if flags is not None else [],
        player=SimpleNamespace(is_dead=player_is_dead),
        game_over=False,
        end_message="",
    )


def check(fake_game) -> None:
    Game._check_end_conditions(fake_game)


def test_no_end_state_with_an_uncaptured_flag_and_player_alive():
    fake = make_fake_game(flags=[make_flag(captured=False)])

    check(fake)

    assert fake.game_over is False


def test_empty_flag_list_does_not_trigger_a_false_victory():
    # A flags=[] game would never actually happen (Map spawns all flags
    # synchronously before Game.update() runs) but the check should still
    # not treat "no flags" as "all flags captured".
    fake = make_fake_game(flags=[])

    check(fake)

    assert fake.game_over is False


def test_victory_once_every_flag_is_captured():
    fake = make_fake_game(flags=[make_flag(captured=True), make_flag(captured=True)])

    check(fake)

    assert fake.game_over is True
    assert fake.end_message == "VICTORY"


def test_no_victory_while_any_flag_is_still_uncaptured():
    fake = make_fake_game(flags=[make_flag(captured=True), make_flag(captured=False)])

    check(fake)

    assert fake.game_over is False


def test_game_over_when_the_player_dies():
    fake = make_fake_game(flags=[make_flag(captured=False)], player_is_dead=True)

    check(fake)

    assert fake.game_over is True
    assert fake.end_message == "GAME OVER"


def test_player_death_takes_priority_over_a_simultaneous_victory():
    fake = make_fake_game(flags=[make_flag(captured=True)], player_is_dead=True)

    check(fake)

    assert fake.end_message == "GAME OVER"
