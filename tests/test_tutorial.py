from collections import defaultdict
from types import SimpleNamespace

import pygame

from gameplay.tutorial import TUTORIAL_STEPS, Tutorial
from util.constants import TUTORIAL_GROUP_GAP, TUTORIAL_ICON_GAP, TUTORIAL_ICON_SIZE


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


def test_move_step_has_a_wasd_group_and_an_arrows_group():
    move_step = TUTORIAL_STEPS[0]

    assert move_step["groups"] == (
        ("keyboard_w", "keyboard_a", "keyboard_s", "keyboard_d"),
        ("keyboard_arrow_up", "keyboard_arrow_left", "keyboard_arrow_down", "keyboard_arrow_right"),
    )


def test_build_group_lays_out_a_four_icon_group_as_a_physical_keyboard_cross(game):
    t = Tutorial(game)

    cluster = t._build_group(("keyboard_w", "keyboard_a", "keyboard_s", "keyboard_d"))

    # 3 icons wide (bottom row) x 2 icons tall (top row + bottom row).
    assert cluster.get_width() == TUTORIAL_ICON_SIZE * 3 + TUTORIAL_ICON_GAP * 2
    assert cluster.get_height() == TUTORIAL_ICON_SIZE * 2 + TUTORIAL_ICON_GAP


def test_build_group_lays_out_a_single_icon_group_as_a_plain_row(game):
    t = Tutorial(game)

    row = t._build_group(("mouse_left",))

    assert row.get_width() == TUTORIAL_ICON_SIZE
    assert row.get_height() == TUTORIAL_ICON_SIZE


def test_build_content_joins_multiple_groups_with_an_or_connector(game):
    t = Tutorial(game)
    step = TUTORIAL_STEPS[0]  # MOVE -- two groups (WASD, arrows)

    content = t._build_content(step)
    wasd_group = t._build_group(step["groups"][0])
    arrows_group = t._build_group(step["groups"][1])

    # Wider than the two groups alone -- there's a connector between them.
    assert content.get_width() > wasd_group.get_width() + arrows_group.get_width()


def test_build_content_skips_the_connector_for_a_single_group(game):
    t = Tutorial(game)
    step = TUTORIAL_STEPS[1]  # FIRE -- one group (mouse_left)

    content = t._build_content(step)
    only_group = t._build_group(step["groups"][0])

    assert content.get_size() == only_group.get_size()


def test_squad_stance_step_stays_hidden_with_no_soldier_in_the_army(game):
    t = Tutorial(game)
    t.step_index = 2  # already past MOVE and FIRE, no soldiers recruited
    surface = pygame.Surface((400, 300))
    surface.fill((0, 0, 0))

    t.draw(surface)

    assert pygame.transform.average_color(surface) == (0, 0, 0, 0)


def test_squad_stance_step_appears_once_a_soldier_is_in_the_army(game):
    t = Tutorial(game)
    t.step_index = 2
    game.soldiers = [SimpleNamespace(is_in_army=True)]
    surface = pygame.Surface((400, 300))
    surface.fill((0, 0, 0))

    t.draw(surface)

    assert pygame.transform.average_color(surface) != (0, 0, 0, 0)


def test_squad_stance_step_stays_hidden_if_soldiers_exist_but_none_are_recruited(game):
    t = Tutorial(game)
    t.step_index = 2
    game.soldiers = [SimpleNamespace(is_in_army=False), SimpleNamespace(is_in_army=False)]
    surface = pygame.Surface((400, 300))
    surface.fill((0, 0, 0))

    t.draw(surface)

    assert pygame.transform.average_color(surface) == (0, 0, 0, 0)


def test_squad_stance_step_can_still_be_completed_while_hidden(game, monkeypatch):
    # The step still advances on Tab even before a soldier is recruited --
    # only *drawing* the prompt is gated, not completing it, so a player
    # who happens to hit Tab early doesn't get stuck.
    t = Tutorial(game)
    t.step_index = 2
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (False, False, False))
    press(game, pygame.K_TAB)

    t.update()

    assert t.done is True
