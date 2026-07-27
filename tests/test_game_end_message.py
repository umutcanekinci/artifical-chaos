"""Game._draw_end_message()/_draw_icon_caption()/_draw_prompt_line() in
isolation -- calling them unbound against a lightweight fake, matching
tests/test_game_end_conditions.py's approach, avoids constructing a real
Game() (which loads the real Tiled map)."""
from types import SimpleNamespace

import pygame

from app.game import Game

pygame.font.init()


def make_fake_game(end_message: str, icon_calls: list, prompt_calls: list):
    # _draw_icon_caption/_draw_prompt_line are stashed directly on the fake
    # instance (plain attributes, not looked up through Game's class
    # hierarchy) since _draw_end_message() is called unbound against this
    # fake, not a real Game -- monkeypatching them on the Game class
    # wouldn't be reachable through self here, same reason
    # _RESTART_EXCLUDED_KEYS in game.py is a module-level constant rather
    # than a class attribute (see test_game_handle_event.py).
    return SimpleNamespace(
        size=(800, 600),
        window=pygame.Surface((800, 600)),
        end_message=end_message,
        _end_font=pygame.font.SysFont("Arial", 40, bold=True),
        _any_key_icon=object(),
        _escape_icon=object(),
        _mouse_icon=object(),
        _draw_icon_caption=lambda icon, parts, top: icon_calls.append((parts, top)) or top + 10,
        _draw_prompt_line=lambda icon, text, top: prompt_calls.append((text, top)) or top + 10,
    )


def test_game_over_draws_the_restart_prompt_and_no_exit_prompt():
    icon_calls, prompt_calls = [], []
    fake = make_fake_game("GAME OVER", icon_calls, prompt_calls)

    Game._draw_end_message(fake)

    assert [parts for parts, _ in icon_calls] == [("or ", fake._mouse_icon, " to restart")]
    assert prompt_calls == []


def test_victory_draws_the_restart_prompt_and_an_exit_prompt():
    icon_calls, prompt_calls = [], []
    fake = make_fake_game("VICTORY", icon_calls, prompt_calls)

    Game._draw_end_message(fake)

    assert [parts for parts, _ in icon_calls] == [("or ", fake._mouse_icon, " to restart")]
    assert [text for text, _ in prompt_calls] == ["Press Esc to exit"]


def test_exit_prompt_is_drawn_below_the_restart_prompt():
    icon_calls, prompt_calls = [], []
    fake = make_fake_game("VICTORY", icon_calls, prompt_calls)

    Game._draw_end_message(fake)

    assert prompt_calls[0][1] > icon_calls[0][1]


def test_draw_icon_caption_renders_something_and_returns_its_bottom():
    fake = SimpleNamespace(size=(800, 600), window=pygame.Surface((800, 600)),
                          _restart_font=pygame.font.SysFont("Arial", 20))
    fake.window.fill((10, 10, 10))
    fake._build_inline = lambda parts: Game._build_inline(fake, parts)
    icon = pygame.Surface((40, 40))
    icon.fill((255, 255, 255))
    mouse_icon = pygame.Surface((20, 20))
    mouse_icon.fill((255, 255, 255))

    bottom = Game._draw_icon_caption(fake, icon, ("or ", mouse_icon, " to restart"), 100)

    assert bottom > 100
    assert pygame.transform.average_color(fake.window) != (10, 10, 10)


def test_build_inline_mixes_text_and_icon_parts_vertically_centered():
    fake = SimpleNamespace(_restart_font=pygame.font.SysFont("Arial", 20))
    icon = pygame.Surface((8, 8), pygame.SRCALPHA)
    icon.fill((255, 255, 255, 255))

    line = Game._build_inline(fake, ("or ", icon, " to restart"))

    text_before = fake._restart_font.render("or ", True, (200, 200, 200))
    text_after = fake._restart_font.render(" to restart", True, (200, 200, 200))
    assert line.get_width() == text_before.get_width() + icon.get_width() + text_after.get_width()
    assert line.get_height() == max(text_before.get_height(), icon.get_height(), text_after.get_height())


def test_draw_prompt_line_renders_something_and_returns_its_bottom():
    fake = SimpleNamespace(size=(800, 600), window=pygame.Surface((800, 600)),
                          _restart_font=pygame.font.SysFont("Arial", 20))
    fake.window.fill((10, 10, 10))
    icon = pygame.Surface((20, 20))
    icon.fill((255, 255, 255))

    bottom = Game._draw_prompt_line(fake, icon, "Press Esc to exit", 100)

    assert bottom > 100
    assert pygame.transform.average_color(fake.window) != (10, 10, 10)
