import pygame

from pygame_core.sprite_sheet import SpriteSheet
from pygame_core.image import scale_by
from pygame_core.ecs.components.animator import Animator, AnimationClip
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


def add_death_clip(obj, path, row: int, *, name: str = "destroyed",
                   size: int = SPRITE_SIZE, fps: float = 6.0) -> None:
    """Register a single-frame, non-looping '<name>_0'/'<name>_1' clip pair.

    Unlike add_directional_clips, this doesn't loop -- Animator.is_playing
    goes False after the one frame, but callers should still gate removal
    with their own timer (a 1-frame clip's "finished" state fires almost
    instantly, before a player could actually see it -- see DESTROYED_DURATION_MS).
    """
    sheet = SpriteSheet.from_path(path)
    animator = obj.get_component(Animator)
    right = scaled_row(sheet, row, 1, size)
    left = [pygame.transform.flip(frame, True, False) for frame in right]
    animator.add_clip(f"{name}_0", AnimationClip(right, fps=fps, loop=False))
    animator.add_clip(f"{name}_1", AnimationClip(left, fps=fps, loop=False))
