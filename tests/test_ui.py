import pygame

from gameplay.ui import draw_bar, draw_radial_progress


class IdentityCamera:
    """world_to_screen/scaled as no-ops -- draw_bar's own math is what's
    under test here, not real camera projection (covered by test_camera.py)."""

    def world_to_screen(self, pos):
        return pygame.Vector2(pos)

    def scaled(self, value):
        return value


def test_draw_bar_fills_proportionally_to_fraction():
    surface = pygame.Surface((100, 20))
    surface.fill((0, 0, 0))

    draw_bar(surface, IdentityCamera(), (50, 10), 80, 10, 0.5, (0, 255, 0))

    # Backing rect spans x=10..90 (centered, width 80). At 50% fill the
    # right half should still be background-black, the left half green.
    assert surface.get_at((15, 10))[:3] == (0, 255, 0)
    assert surface.get_at((85, 10))[:3] == (0, 0, 0)


def test_draw_bar_clamps_fraction_above_one():
    surface = pygame.Surface((100, 20))
    surface.fill((10, 10, 10))

    draw_bar(surface, IdentityCamera(), (50, 10), 80, 10, 5.0, (0, 255, 0))

    # Fill can't overflow the backing rect even with a fraction > 1.
    assert surface.get_at((89, 10))[:3] == (0, 255, 0)


def test_draw_bar_with_zero_fraction_draws_only_the_backing_color():
    surface = pygame.Surface((100, 20))
    surface.fill((5, 5, 5))

    draw_bar(surface, IdentityCamera(), (50, 10), 80, 10, 0.0, (0, 255, 0),
             back_color=(1, 2, 3))

    assert surface.get_at((50, 10))[:3] == (1, 2, 3)


# draw_radial_progress sweeps clockwise from 12 o'clock. Sample points use
# a radius comfortably inside the drawn ellipse (avoids anti-aliasing/edge
# pixels at the exact boundary). RX != RY throughout so these also exercise
# the elliptical (non-circular) case, not just a circle with two equal args.
CENTER = (100, 100)
RX, RY = 60, 30
TOP           = (CENTER[0], CENTER[1] - RY // 2)  # 12 o'clock
RIGHT         = (CENTER[0] + RX // 2, CENTER[1])  # 3 o'clock
BOTTOM        = (CENTER[0], CENTER[1] + RY // 2)  # 6 o'clock
UPPER_RIGHT   = (CENTER[0] + RX // 3, CENTER[1] - RY // 3)  # ~1:30
LOWER_LEFT    = (CENTER[0] - RX // 3, CENTER[1] + RY // 3)  # ~7:30


def test_draw_radial_progress_zero_fraction_draws_only_the_backing_ellipse():
    surface = pygame.Surface((200, 200))
    surface.fill((5, 5, 5))

    draw_radial_progress(surface, IdentityCamera(), CENTER, RX, RY, 0.0,
                         (0, 255, 0), back_color=(1, 2, 3))

    assert surface.get_at(TOP)[:3] == (1, 2, 3)


def test_draw_radial_progress_full_fraction_fills_the_whole_ellipse():
    surface = pygame.Surface((200, 200))
    surface.fill((5, 5, 5))

    draw_radial_progress(surface, IdentityCamera(), CENTER, RX, RY, 1.0, (0, 255, 0))

    for point in (TOP, RIGHT, BOTTOM, UPPER_RIGHT, LOWER_LEFT):
        assert surface.get_at(point)[:3] == (0, 255, 0)


def test_draw_radial_progress_quarter_fill_covers_only_the_first_clockwise_quadrant():
    surface = pygame.Surface((200, 200))
    surface.fill((5, 5, 5))

    draw_radial_progress(surface, IdentityCamera(), CENTER, RX, RY, 0.25, (0, 255, 0))

    assert surface.get_at(UPPER_RIGHT)[:3] == (0, 255, 0)  # within the first quadrant swept
    assert surface.get_at(LOWER_LEFT)[:3] == (0, 0, 0)  # backing default -- still unfilled


def test_draw_radial_progress_ellipse_is_wider_than_tall_when_rx_exceeds_ry():
    surface = pygame.Surface((200, 200))
    surface.fill((5, 5, 5))

    draw_radial_progress(surface, IdentityCamera(), CENTER, RX, RY, 1.0, (0, 255, 0))

    # A point beyond RY vertically but within RX horizontally must be
    # outside the ellipse -- proof rx/ry are applied independently, not
    # just the larger of the two used for both axes.
    assert surface.get_at((CENTER[0], CENTER[1] - RY - 10))[:3] == (5, 5, 5)
    assert surface.get_at((CENTER[0] + RX - 5, CENTER[1]))[:3] == (0, 255, 0)


def test_draw_radial_progress_alpha_blends_instead_of_a_solid_fill():
    surface = pygame.Surface((200, 200))
    surface.fill((0, 0, 0))

    draw_radial_progress(surface, IdentityCamera(), CENTER, RX, RY, 1.0, (0, 255, 0), alpha=128)

    r, g, b = surface.get_at(CENTER)[:3]
    assert (r, g, b) != (0, 255, 0)  # not a fully opaque fill
    assert (r, g, b) != (0, 0, 0)    # not fully transparent either
    assert 0 < g < 255               # genuinely blended with the background
