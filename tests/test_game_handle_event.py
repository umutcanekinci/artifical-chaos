"""Game.handle_event() in isolation -- calling the real unbound method
against a lightweight stand-in avoids constructing a full Game() (which
loads the real Tiled map), matching tests/test_game_end_conditions.py's
approach."""
from types import SimpleNamespace

import pygame

from app.game import Game


def make_fake_game(*, game_over=False):
    toggles = []
    restarts = []
    fake = SimpleNamespace(
        player=SimpleNamespace(toggle_squad_stance=lambda: toggles.append(1)),
        game_over=game_over,
        restart=lambda: restarts.append(1),
    )
    return fake, toggles, restarts


def test_tab_keydown_toggles_the_squad_stance():
    fake, toggles, restarts = make_fake_game()

    Game.handle_event(fake, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))

    assert len(toggles) == 1
    assert len(restarts) == 0


def test_other_keydowns_do_not_toggle_the_squad_stance():
    fake, toggles, restarts = make_fake_game()

    Game.handle_event(fake, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a))

    assert len(toggles) == 0
    assert len(restarts) == 0


def test_non_keydown_events_do_not_toggle_the_squad_stance():
    fake, toggles, restarts = make_fake_game()

    Game.handle_event(fake, pygame.event.Event(pygame.KEYUP, key=pygame.K_TAB))

    assert len(toggles) == 0
    assert len(restarts) == 0


def test_any_keydown_restarts_once_the_run_has_ended():
    fake, toggles, restarts = make_fake_game(game_over=True)

    Game.handle_event(fake, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a))

    assert len(restarts) == 1


def test_mouse_click_restarts_once_the_run_has_ended():
    fake, toggles, restarts = make_fake_game(game_over=True)

    Game.handle_event(fake, pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1))

    assert len(restarts) == 1


def test_tab_restarts_rather_than_toggling_stance_once_the_run_has_ended():
    # game_over short-circuits handle_event() entirely -- Tab isn't in the
    # excluded-keys set, so it restarts like any other key instead of
    # reaching the stance-toggle branch.
    fake, toggles, restarts = make_fake_game(game_over=True)

    Game.handle_event(fake, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB))

    assert len(restarts) == 1
    assert len(toggles) == 0


def test_escape_does_not_restart_once_the_run_has_ended():
    fake, toggles, restarts = make_fake_game(game_over=True)

    Game.handle_event(fake, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))

    assert len(restarts) == 0


def test_f1_does_not_restart_once_the_run_has_ended():
    fake, toggles, restarts = make_fake_game(game_over=True)

    Game.handle_event(fake, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F1))

    assert len(restarts) == 0


def test_f11_does_not_restart_once_the_run_has_ended():
    fake, toggles, restarts = make_fake_game(game_over=True)

    Game.handle_event(fake, pygame.event.Event(pygame.KEYDOWN, key=pygame.K_F11))

    assert len(restarts) == 0


def test_keyup_does_not_restart_once_the_run_has_ended():
    fake, toggles, restarts = make_fake_game(game_over=True)

    Game.handle_event(fake, pygame.event.Event(pygame.KEYUP, key=pygame.K_a))

    assert len(restarts) == 0
