import pygame
import pytest

from gameplay.camera import FollowCamera


def make_camera(viewport=(800, 600), map_size=(2000, 1500)) -> FollowCamera:
    rect = pygame.Rect(0, 0, *viewport)
    return FollowCamera(rect, map_width=map_size[0], map_height=map_size[1])


def test_follow_centers_the_target_when_within_bounds():
    cam = make_camera()

    cam.follow((1000, 750))  # map center

    assert cam._offset.x == pytest.approx(800 / 2 - 1000)
    assert cam._offset.y == pytest.approx(600 / 2 - 750)


def test_follow_clamps_at_the_top_left_map_edge():
    cam = make_camera()

    cam.follow((0, 0))  # would want a positive offset, past the map origin

    assert cam._offset.x == 0
    assert cam._offset.y == 0


def test_follow_clamps_at_the_bottom_right_map_edge():
    cam = make_camera(viewport=(800, 600), map_size=(2000, 1500))

    cam.follow((2000, 1500))

    assert cam._offset.x == 800 - 2000
    assert cam._offset.y == 600 - 1500


def test_follow_locks_offset_to_zero_when_map_smaller_than_viewport():
    cam = make_camera(viewport=(800, 600), map_size=(400, 300))

    cam.follow((200, 150))  # map center

    assert cam._offset.x == 0
    assert cam._offset.y == 0


def test_follow_scales_the_target_position_by_zoom():
    cam = make_camera()
    cam.scale = 2.0

    cam.follow((500, 400))

    assert cam._offset.x == pytest.approx(800 / 2 - 500 * 2.0)
    assert cam._offset.y == pytest.approx(600 / 2 - 400 * 2.0)
