import pygame

from pygame_core.image import load_image
from pygame_core.asset_path import ImagePath

from util.constants import (
    TUTORIAL_FONT_SIZE, TUTORIAL_ICON_GAP, TUTORIAL_ICON_SIZE,
    TUTORIAL_PANEL_ALPHA, TUTORIAL_PANEL_PADDING, TUTORIAL_TOP_MARGIN,
)

_MOVE_KEYS = (
    pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d,
    pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT,
)


def _moved(game) -> bool:
    return any(game.keys[k] for k in _MOVE_KEYS)


def _fired(game) -> bool:
    return pygame.mouse.get_pressed()[0]


def _toggled_stance(game) -> bool:
    return game.keys[pygame.K_TAB]


# Each step advances the instant the player performs the input at all, not
# once the corresponding game action actually lands -- e.g. FIRE completes
# on the mouse button going down, not on a shot hitting a drone, since one
# might not even be in range yet the first time the player tries.
TUTORIAL_STEPS = (
    {"label": "MOVE", "icons": ("keyboard_w", "keyboard_a", "keyboard_s", "keyboard_d"), "check": _moved},
    {"label": "FIRE", "icons": ("mouse_left",), "check": _fired},
    {"label": "SQUAD STANCE", "icons": ("keyboard_tab",), "check": _toggled_stance},
)


class Tutorial:
    """A short linear "press this key" onboarding overlay shown at the start
    of a run. Not a GameObject -- pure screen-space HUD with no world
    position, constructed once in Game.__init__ and driven explicitly from
    Game.update()/draw() the same way _draw_end_message() is, rather than
    living in game.all_sprites.

    Steps advance one at a time (see TUTORIAL_STEPS); once every step is
    done, draw() stops rendering anything and update() stops doing any
    work. There's no way to bring it back and nothing persists it across
    runs -- this project has no save/load yet (see CLAUDE.md's Persistence
    note), so "not persistent" here just means "never shown again this
    process" rather than something backed by a save file.
    """

    def __init__(self, game) -> None:
        self.game = game
        self.step_index = 0
        self._font = pygame.font.SysFont("Arial", TUTORIAL_FONT_SIZE, bold=True)

    @property
    def done(self) -> bool:
        return self.step_index >= len(TUTORIAL_STEPS)

    def update(self) -> None:
        if self.done:
            return
        if TUTORIAL_STEPS[self.step_index]["check"](self.game):
            self.step_index += 1

    def draw(self, surface: pygame.Surface) -> None:
        if self.done:
            return
        step = TUTORIAL_STEPS[self.step_index]
        icons = [load_image(ImagePath(name, "input_prompts"), size=(TUTORIAL_ICON_SIZE, TUTORIAL_ICON_SIZE))
                for name in step["icons"]]

        label = self._font.render(step["label"], True, (255, 255, 255))
        icons_width = len(icons) * TUTORIAL_ICON_SIZE + (len(icons) - 1) * TUTORIAL_ICON_GAP
        panel_width = max(label.get_width(), icons_width) + TUTORIAL_PANEL_PADDING * 2
        panel_height = TUTORIAL_ICON_SIZE + label.get_height() + TUTORIAL_PANEL_PADDING * 3

        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, TUTORIAL_PANEL_ALPHA), panel.get_rect(), border_radius=8)

        label_rect = label.get_rect(midtop=(panel_width // 2, TUTORIAL_PANEL_PADDING))
        panel.blit(label, label_rect)

        x = (panel_width - icons_width) // 2
        y = label_rect.bottom + TUTORIAL_PANEL_PADDING
        for icon in icons:
            panel.blit(icon, (x, y))
            x += TUTORIAL_ICON_SIZE + TUTORIAL_ICON_GAP

        rect = panel.get_rect(midtop=(surface.get_width() // 2, TUTORIAL_TOP_MARGIN))
        surface.blit(panel, rect)
