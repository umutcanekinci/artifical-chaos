import pygame

from pygamine import load_image
from pygamine import ImagePath

from util.constants import (
    TUTORIAL_FONT_SIZE, TUTORIAL_GROUP_GAP, TUTORIAL_ICON_GAP, TUTORIAL_ICON_SIZE,
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


def _always_ready(game) -> bool:
    return True


def _has_a_soldier(game) -> bool:
    return any(s.is_in_army for s in game.soldiers)


# Each step advances the instant the player performs the input at all, not
# once the corresponding game action actually lands -- e.g. FIRE completes
# on the mouse button going down, not on a shot hitting a drone, since one
# might not even be in range yet the first time the player tries.
#
# "groups" is a tuple of icon-name tuples, one group per equivalent input
# (MOVE has two: WASD or arrow keys -- either moves). A 4-icon group renders
# as a physical keyboard cross cluster (see Tutorial._build_group), matching
# how WASD/arrow keys actually sit on a real keyboard; anything else renders
# as a plain row. Multiple groups are joined with an "OR" connector.
#
# "ready" gates whether draw() shows the step at all -- SQUAD STANCE only
# means anything once a soldier's actually in the army (toggling a stance
# with no squad to apply it to is meaningless), so it stays hidden until
# then even though it's already the current step; MOVE/FIRE have nothing to
# wait on beyond the previous step finishing, which the linear step_index
# sequencing already guarantees.
TUTORIAL_STEPS = (
    {
        "label": "MOVE",
        "groups": (
            ("keyboard_w", "keyboard_a", "keyboard_s", "keyboard_d"),
            ("keyboard_arrow_up", "keyboard_arrow_left", "keyboard_arrow_down", "keyboard_arrow_right"),
        ),
        "check": _moved,
        "ready": _always_ready,
    },
    {"label": "FIRE", "groups": (("mouse_left",),), "check": _fired, "ready": _always_ready},
    {"label": "SQUAD STANCE", "groups": (("keyboard_tab",),), "check": _toggled_stance, "ready": _has_a_soldier},
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

    def _build_group(self, names: tuple) -> pygame.Surface:
        icons = [load_image(ImagePath(name, "input_prompts"), size=(TUTORIAL_ICON_SIZE, TUTORIAL_ICON_SIZE))
                for name in names]

        if len(icons) != 4:
            width = len(icons) * TUTORIAL_ICON_SIZE + (len(icons) - 1) * TUTORIAL_ICON_GAP
            surface = pygame.Surface((width, TUTORIAL_ICON_SIZE), pygame.SRCALPHA)
            x = 0
            for icon in icons:
                surface.blit(icon, (x, 0))
                x += TUTORIAL_ICON_SIZE + TUTORIAL_ICON_GAP
            return surface

        # Physical keyboard cross cluster: icons[0] centered on top (W /
        # up-arrow), icons[1:] in a row below it left-to-right (A-S-D /
        # left-down-right) -- the same layout those keys actually sit in.
        width = TUTORIAL_ICON_SIZE * 3 + TUTORIAL_ICON_GAP * 2
        height = TUTORIAL_ICON_SIZE * 2 + TUTORIAL_ICON_GAP
        surface = pygame.Surface((width, height), pygame.SRCALPHA)
        surface.blit(icons[0], (TUTORIAL_ICON_SIZE + TUTORIAL_ICON_GAP, 0))
        bottom_y = TUTORIAL_ICON_SIZE + TUTORIAL_ICON_GAP
        for i, icon in enumerate(icons[1:]):
            surface.blit(icon, (i * (TUTORIAL_ICON_SIZE + TUTORIAL_ICON_GAP), bottom_y))
        return surface

    def _build_content(self, step) -> pygame.Surface:
        groups = [self._build_group(names) for names in step["groups"]]
        connector = self._font.render("OR", True, (200, 200, 200)) if len(groups) > 1 else None

        parts = []
        for i, group in enumerate(groups):
            if i > 0:
                parts.append(connector)
            parts.append(group)

        width = sum(p.get_width() for p in parts) + TUTORIAL_GROUP_GAP * (len(parts) - 1)
        height = max(p.get_height() for p in parts)
        content = pygame.Surface((width, height), pygame.SRCALPHA)

        x = 0
        for part in parts:
            content.blit(part, (x, (height - part.get_height()) // 2))
            x += part.get_width() + TUTORIAL_GROUP_GAP
        return content

    def draw(self, surface: pygame.Surface) -> None:
        if self.done:
            return
        step = TUTORIAL_STEPS[self.step_index]
        if not step["ready"](self.game):
            return
        content = self._build_content(step)

        label = self._font.render(step["label"], True, (255, 255, 255))
        panel_width = max(label.get_width(), content.get_width()) + TUTORIAL_PANEL_PADDING * 2
        panel_height = content.get_height() + label.get_height() + TUTORIAL_PANEL_PADDING * 3

        panel = pygame.Surface((panel_width, panel_height), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, TUTORIAL_PANEL_ALPHA), panel.get_rect(), border_radius=8)

        label_rect = label.get_rect(midtop=(panel_width // 2, TUTORIAL_PANEL_PADDING))
        panel.blit(label, label_rect)

        content_rect = content.get_rect(midtop=(panel_width // 2, label_rect.bottom + TUTORIAL_PANEL_PADDING))
        panel.blit(content, content_rect)

        rect = panel.get_rect(midtop=(surface.get_width() // 2, TUTORIAL_TOP_MARGIN))
        surface.blit(panel, rect)
