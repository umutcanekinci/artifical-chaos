import pygame

from pygamine import ImagePath
from pygamine import Animator
from pygamine import GameObject
from pygamine import SpriteSheet

from gameplay.animation import add_directional_clips, scaled_row
from util.constants import SCALE_FACTOR, SPRITE_SIZE

# Scarab's sheet has row 0 (idle) and row 1 (walking) -- same one Scarab
# itself loads in gameplay/robot.py, so this exercises the real asset.
SCARAB_SHEET = ImagePath("Scarab", "robots")


def make_animated_object() -> GameObject:
    obj = GameObject()
    obj.add_component(Animator)
    return obj


def test_scaled_row_returns_the_requested_frame_count():
    sheet = SpriteSheet.from_path(SCARAB_SHEET)
    frames = scaled_row(sheet, row=0, count=2, size=SPRITE_SIZE)
    assert len(frames) == 2


def test_scaled_row_scales_each_frame_by_scale_factor():
    sheet = SpriteSheet.from_path(SCARAB_SHEET)
    frames = scaled_row(sheet, row=0, count=1, size=SPRITE_SIZE)
    assert frames[0].get_size() == (SPRITE_SIZE * SCALE_FACTOR, SPRITE_SIZE * SCALE_FACTOR)


def test_add_directional_clips_registers_right_and_left_variants():
    obj = make_animated_object()
    add_directional_clips(obj, SCARAB_SHEET, {"idle": 0})

    animator = obj.get_component(Animator)
    assert set(animator.clips) == {"idle_0", "idle_1"}


def test_add_directional_clips_left_variant_is_horizontally_flipped():
    obj = make_animated_object()
    add_directional_clips(obj, SCARAB_SHEET, {"idle": 0}, frame_count=1)

    animator = obj.get_component(Animator)
    right_frame = animator.clips["idle_0"].frames[0]
    left_frame = animator.clips["idle_1"].frames[0]
    expected_flip = pygame.transform.flip(right_frame, True, False)

    assert pygame.image.tobytes(left_frame, "RGBA") == pygame.image.tobytes(expected_flip, "RGBA")


def test_add_directional_clips_registers_one_pair_per_row():
    obj = make_animated_object()
    add_directional_clips(obj, SCARAB_SHEET, {"idle": 0, "walking": 1})

    animator = obj.get_component(Animator)
    assert set(animator.clips) == {"idle_0", "idle_1", "walking_0", "walking_1"}
