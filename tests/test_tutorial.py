from collections import defaultdict

import pygame

from gameplay.tutorial import TUTORIAL_STEPS, Tutorial


def press(game, *keys) -> None:
    game.keys = defaultdict(bool, {k: True for k in keys})


def test_starts_on_the_first_step_not_done(game):
    t = Tutorial(game)

    assert t.step_index == 0
    assert t.done is False


def test_move_step_advances_on_any_movement_key(game):
    t = Tutorial(game)
    press(game, pygame.K_d)

    t.update()

    assert t.step_index == 1


def test_move_step_does_not_advance_with_no_input(game):
    t = Tutorial(game)

    t.update()

    assert t.step_index == 0


def test_fire_step_advances_on_left_mouse_button(game, monkeypatch):
    t = Tutorial(game)
    t.step_index = 1  # already past MOVE
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (True, False, False))

    t.update()

    assert t.step_index == 2


def test_fire_step_does_not_advance_on_right_click(game, monkeypatch):
    t = Tutorial(game)
    t.step_index = 1
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (False, False, True))

    t.update()

    assert t.step_index == 1


def test_squad_stance_step_advances_and_completes_the_tutorial(game, monkeypatch):
    t = Tutorial(game)
    t.step_index = 2  # already past MOVE and FIRE
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (False, False, False))
    press(game, pygame.K_TAB)

    t.update()

    assert t.done is True
    assert t.step_index == len(TUTORIAL_STEPS)


def test_update_is_a_no_op_once_done(game):
    t = Tutorial(game)
    t.step_index = len(TUTORIAL_STEPS)

    t.update()

    assert t.step_index == len(TUTORIAL_STEPS)


def test_draw_renders_something_for_the_current_step(game):
    t = Tutorial(game)
    surface = pygame.Surface((400, 300))
    surface.fill((0, 0, 0))

    t.draw(surface)

    assert pygame.transform.average_color(surface) != (0, 0, 0)


def test_draw_does_nothing_once_done(game):
    t = Tutorial(game)
    t.step_index = len(TUTORIAL_STEPS)
    surface = pygame.Surface((400, 300))
    surface.fill((0, 0, 0))

    t.draw(surface)

    assert pygame.transform.average_color(surface) == (0, 0, 0, 0)
