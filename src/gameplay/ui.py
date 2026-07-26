import math

import pygame

from util.constants import HP_BAR_CRITICAL, HP_BAR_GAP, HP_BAR_HEALTHY, HP_BAR_HEIGHT, HP_BAR_HURT, HP_BAR_WIDTH


def draw_bar(surface, camera, world_pos, width: int, height: int,
             fraction: float, fill_color, *, back_color=(0, 0, 0)) -> None:
    """Draws a simple two-rect progress bar (black backing + a colored
    fill), centered at a world position and scaled through the camera.

    `width`/`height` are world-space sizes (already including SCALE_FACTOR,
    same convention as every entity's `rect`), not screen pixels -- callers
    don't need to call camera.scaled() themselves.
    """
    fraction = max(0.0, min(1.0, fraction))
    screen_width, screen_height = camera.scaled(width), camera.scaled(height)
    center = camera.world_to_screen(world_pos)

    back_rect = pygame.Rect(0, 0, screen_width, screen_height)
    back_rect.center = (center.x, center.y)
    pygame.draw.rect(surface, back_color, back_rect)

    fill_rect = back_rect.copy()
    fill_rect.width = int(screen_width * fraction)
    pygame.draw.rect(surface, fill_color, fill_rect)


def draw_radial_progress(surface, camera, world_pos, radius_x: int, radius_y: int, fraction: float,
                         fill_color, *, back_color=(0, 0, 0), segments: int = 32, alpha: int = 255) -> None:
    """Draws a pie-slice radial fill (a "clock hand" sweep starting at 12
    o'clock, clockwise) centered at a world position -- an elliptical
    capture meter (`radius_x`/`radius_y` independently, so it doesn't have
    to be a circle; pass equal values for one). Both are world-space sizes
    (see draw_bar's convention).

    Draws the empty backing ellipse first (so callers can layer this behind
    a sprite and still show the unfilled portion), then the filled wedge on
    top, unless fraction is 0 (nothing to fill) or >= 1 (just a solid
    ellipse -- a pie slice can't sweep a full 360 degrees as one polygon).

    `alpha` (0-255, opaque by default) applies to both -- pygame.draw
    ignores a color's alpha channel on a non-per-pixel-alpha target (the
    game window included), so this renders onto a small SRCALPHA scratch
    surface first and blits that, the same trick Game._draw_end_message()
    uses for its overlay.
    """
    fraction = max(0.0, min(1.0, fraction))
    center = camera.world_to_screen(world_pos)
    screen_rx, screen_ry = camera.scaled(radius_x), camera.scaled(radius_y)
    size = (int(screen_rx * 2), int(screen_ry * 2))

    layer = pygame.Surface(size, pygame.SRCALPHA)
    bounds = layer.get_rect()
    local_center = bounds.center

    pygame.draw.ellipse(layer, (*back_color, alpha), bounds)
    if fraction > 0.0:
        if fraction >= 1.0:
            pygame.draw.ellipse(layer, (*fill_color, alpha), bounds)
        else:
            start_angle = -math.pi / 2  # 12 o'clock
            sweep = fraction * 2 * math.pi
            steps = max(1, int(segments * fraction))
            points = [local_center]
            for i in range(steps + 1):
                angle = start_angle + sweep * i / steps
                points.append((local_center[0] + screen_rx * math.cos(angle),
                               local_center[1] + screen_ry * math.sin(angle)))
            pygame.draw.polygon(layer, (*fill_color, alpha), points)

    surface.blit(layer, layer.get_rect(center=(center.x, center.y)))


def draw_health_bar(surface, camera, rect, hp: float, max_hp: float, *, always: bool = False) -> None:
    """Draws an overhead HP bar above `rect`, colored by health tier
    (HP_BAR_HEALTHY/HURT/CRITICAL). Skipped entirely at full health unless
    `always=True` -- the player's own bar is worth showing proactively,
    but a full-health soldier/drone doesn't need one cluttering the screen;
    it'll appear the moment they take their first hit."""
    fraction = max(0.0, hp) / max_hp
    if fraction >= 1.0 and not always:
        return

    if fraction >= 0.6:
        color = HP_BAR_HEALTHY
    elif fraction >= 0.3:
        color = HP_BAR_HURT
    else:
        color = HP_BAR_CRITICAL

    position = (rect.centerx, rect.top - HP_BAR_GAP)
    draw_bar(surface, camera, position, HP_BAR_WIDTH, HP_BAR_HEIGHT, fraction, color)
