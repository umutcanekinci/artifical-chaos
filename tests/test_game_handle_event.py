"""Game.handle_event() in isolation -- calling the real unbound method
against a lightweight stand-in avoids constructing a full Game() (which
loads the real Tiled map), matching tests/test_game_end_conditions.py's
approach."""
from types import SimpleNamespace

import pygame

from app.game import Game


def make_fake_game():
    toggles = []
    return SimpleNamespace(player=SimpleNamespace(toggle_squad_stance=lambda: toggles.append(1))), toggles


def test_tab_keydown_toggles_the_squad_stance():
    fake, toggles = make_fake_game()

    Game.handle_event(fake, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))

    assert len(toggles) == 1


def test_other_keydowns_do_not_toggle_the_squad_stance():
    fake, toggles = make_fake_game()

    Game.handle_event(fake, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a))

    assert len(toggles) == 0


def test_non_keydown_events_do_not_toggle_the_squad_stance():
    fake, toggles = make_fake_game()

    Game.handle_event(fake, pygame.event.Event(pygame.KEYUP, key=pygame.K_TAB))

    assert len(toggles) == 0
