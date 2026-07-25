"""Game._check_end_conditions() in isolation -- calling the real unbound
method against a lightweight stand-in avoids constructing a full Game()
(which loads the real Tiled map) for what's really a small state-machine
test."""
from types import SimpleNamespace

from app.game import Game


def make_fake_game(*, robots=None, player_is_dead=False, robots_ever_present=False):
    return SimpleNamespace(
        robots=robots if robots is not None else [],
        player=SimpleNamespace(is_dead=player_is_dead),
        _robots_ever_present=robots_ever_present,
        game_over=False,
        end_message="",
    )


def check(fake_game) -> None:
    Game._check_end_conditions(fake_game)


def test_no_end_state_with_robots_still_alive_and_player_alive():
    fake = make_fake_game(robots=["scarab"])

    check(fake)

    assert fake.game_over is False
    assert fake._robots_ever_present is True


def test_empty_map_at_startup_does_not_trigger_a_false_victory():
    # robots=[] from the very first check (nothing has spawned/died) must
    # not look identical to "all robots defeated".
    fake = make_fake_game(robots=[])

    check(fake)

    assert fake.game_over is False


def test_victory_once_all_robots_are_gone_after_having_existed():
    fake = make_fake_game(robots=[], robots_ever_present=True)

    check(fake)

    assert fake.game_over is True
    assert fake.end_message == "VICTORY"


def test_game_over_when_the_player_dies():
    fake = make_fake_game(robots=["scarab"], player_is_dead=True)

    check(fake)

    assert fake.game_over is True
    assert fake.end_message == "GAME OVER"


def test_player_death_takes_priority_over_a_simultaneous_victory():
    fake = make_fake_game(robots=[], robots_ever_present=True, player_is_dead=True)

    check(fake)

    assert fake.end_message == "GAME OVER"


def test_robots_ever_present_latches_true_and_stays_true():
    fake = make_fake_game(robots=["scarab"])
    check(fake)
    assert fake._robots_ever_present is True

    fake.robots = []
    check(fake)  # should now detect victory using the latched flag

    assert fake.game_over is True
    assert fake.end_message == "VICTORY"
