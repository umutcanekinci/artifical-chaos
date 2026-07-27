"""Shared pytest setup and fixtures for artifical-chaos's app-level test suite.

Run from the repo root (`uv run pytest`, matching how __main__.py assumes
cwd == repo root for its own asset-relative paths).
"""

import os
from collections import defaultdict
from types import SimpleNamespace

# Dummy SDL drivers so pygame can run headless (e.g. in CI) without opening a
# real window or probing for a sound device. Must be set before pygame is
# imported anywhere.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest
from pygame.math import Vector2

pygame.init()
# Player/Soldier/Footprint/Scarab/Flag load images via convert_alpha(), which
# raises without a display surface. Application.__init__ normally provides
# one; these tests construct game objects directly, with no Application/Game
# involved, so they need their own.
pygame.display.set_mode((1, 1))


class FakeGame:
    """Minimal stand-in for app.game.Game -- provides just what
    Player/Soldier/Footprint/Scarab/Flag touch during construction/update.

    self.keys is a defaultdict(bool): pygame's real ScancodeWrapper returns
    False for any unpressed key, so unset entries here default the same way
    instead of KeyErroring.

    self.player defaults to a plain stand-in (position/velocity/hp/active/
    rank_up) rather than None, since drones/soldiers read game.player.
    position every tick regardless of whether the test cares about the real
    Player class, Flag.update() calls game.player.rank_up() the instant a
    flag's progress reaches 100 (see gameplay/flag.py) -- a no-op stand-in
    here means a test driving an unrelated flag to capture doesn't need to
    know about rank-up at all -- and Soldier.engage() reads game.player.
    velocity and game.player.squad_stance every tick too (see
    SQUAD_ATTACK_MAX_PLAYER_SPEED / SQUAD_GUARD_* in util/constants.py),
    defaulting to the zero vector and "engage" so a soldier test that
    doesn't care about player movement/stance still gets treated as
    "stationary" and unrestricted (able to actually land hits, same as
    before the stance toggle existed) rather than erroring on a missing
    attribute.
    """

    def __init__(self):
        self.all_sprites: list = []
        self.walls: list = []
        self.flags: list = []
        self.soldiers: list = []
        self.robots: list = []
        self.keys: dict = defaultdict(bool)
        self.delta_time: float = 1 / 60
        self.player = SimpleNamespace(
            position=Vector2(0, 0), velocity=Vector2(0, 0), hp=100, active=True, rank_up=lambda: None,
            squad_stance="engage")


@pytest.fixture
def game() -> FakeGame:
    return FakeGame()


@pytest.fixture
def fake_ticks(monkeypatch):
    """A controllable stand-in for pygame.time.get_ticks().

    Set fake_ticks["t"] = <ms> to move the clock without real sleeps, for
    deterministic tests of footprint spacing / lifetimes.
    """
    state = {"t": 0}
    monkeypatch.setattr(pygame.time, "get_ticks", lambda: state["t"])
    return state
