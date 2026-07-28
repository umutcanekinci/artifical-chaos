"""Game.update()'s delta_time clamp in isolation -- calling the real unbound
method against a lightweight stand-in avoids constructing a full Game()
(which loads the real Tiled map), same pattern as test_game_end_conditions.py.

Regression coverage for a real bug: pygame.time.Clock.get_time() measures
wall-clock time since the last tick() call, so a slow synchronous restart()
(rebuilding the whole map from the tmx) lands its entire cost inside the
*next* frame's delta_time as one giant spike -- and because Player/Soldier/
Drone.move() is quadratic in delta_time, an unclamped spike combined with a
held movement key could teleport an entity thousands of units in a single
frame, tunneling through walls or landing outside the map."""
from types import SimpleNamespace

from app.game import Game
from util.constants import MAX_DELTA_TIME


def make_fake_game(*, clock_ms: float):
    fake = SimpleNamespace(
        game_over=False,
        clock=SimpleNamespace(get_time=lambda: clock_ms),
        camera=SimpleNamespace(follow=lambda *_: None),
        all_sprites=SimpleNamespace(update=lambda: None),
        tutorial=SimpleNamespace(update=lambda: None),
        player=SimpleNamespace(rect=SimpleNamespace(center=(0, 0)), is_dead=False),
        flags=[],
    )
    fake._purge_inactive = lambda: None
    fake._check_end_conditions = lambda: None
    return fake


def test_delta_time_matches_the_clock_under_normal_conditions():
    fake = make_fake_game(clock_ms=16)  # a normal ~60fps frame

    Game.update(fake)

    assert fake.delta_time == 16 / 1000


def test_delta_time_is_clamped_after_a_huge_clock_spike():
    # e.g. the ~1s a real restart() takes to rebuild the map landing inside
    # this frame's Clock.get_time() reading.
    fake = make_fake_game(clock_ms=1860)

    Game.update(fake)

    assert fake.delta_time == MAX_DELTA_TIME


def test_delta_time_is_exactly_the_clamp_at_the_boundary():
    boundary_ms = MAX_DELTA_TIME * 1000
    fake = make_fake_game(clock_ms=boundary_ms)

    Game.update(fake)

    assert fake.delta_time == MAX_DELTA_TIME
