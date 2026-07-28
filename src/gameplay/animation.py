import pygame

from pygame_core.sprite_sheet import SpriteSheet
from pygame_core.image import scale_by
from pygame_core.ecs.components.animator import Animator
from pygame_core.ecs.components.animation_clip import AnimationClip
from util.constants import SPRITE_SIZE, SCALE_FACTOR


def scaled_row(sheet: SpriteSheet, row: int, count: int, size: int) -> list[pygame.Surface]:
    """Slice `count` frames from one sheet row and scale each by SCALE_FACTOR."""
    return [scale_by(sheet.frame(i, row, size, size), SCALE_FACTOR) for i in range(count)]


def add_directional_clips(obj, path, rows: dict[str, int], *, frame_count: int = 2,
                          size: int = SPRITE_SIZE, fps: float = 6.0) -> None:
    """Register '<name>_0' (right) and '<name>_1' (left, h-flipped) clips on obj's Animator.

    `rows` maps a clip base-name to its sheet row, e.g. {"idle": 0, "walking": 1}.
    Play them as f"{status}_{facing}" where facing 0 = right, 1 = left.
    """
    sheet = SpriteSheet.from_path(path)
    animator = obj.get_component(Animator)
    for name, row in rows.items():
        right = scaled_row(sheet, row, frame_count, size)
        left = [pygame.transform.flip(frame, True, False) for frame in right]
        animator.add_clip(f"{name}_0", AnimationClip(right, fps=fps, loop=True))
        animator.add_clip(f"{name}_1", AnimationClip(left, fps=fps, loop=True))


def add_oneshot_clip(obj, path, row: int, frame_count: int = 1, *, name: str = "destroyed",
                     size: int = SPRITE_SIZE, fps: float = 6.0) -> None:
    """Register a non-looping '<name>_0'/'<name>_1' clip pair that plays
    frame_count frames once.

    With frame_count=1 (the default -- used for drones' single destroyed
    frame), Animator.is_playing goes False almost instantly, before a
    player could actually see it, so callers holding a single-frame pose
    need their own duration timer (see DESTROYED_DURATION_MS) rather than
    gating removal on is_playing. Multi-frame callers (gameplay/effects.py)
    don't have that problem -- the clip actually takes visible time to play
    through, so they gate removal on is_playing directly.
    """
    sheet = SpriteSheet.from_path(path)
    animator = obj.get_component(Animator)
    right = scaled_row(sheet, row, frame_count, size)
    left = [pygame.transform.flip(frame, True, False) for frame in right]
    animator.add_clip(f"{name}_0", AnimationClip(right, fps=fps, loop=False))
    animator.add_clip(f"{name}_1", AnimationClip(left, fps=fps, loop=False))
