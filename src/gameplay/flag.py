import pygame
from pygame.math import Vector2
from typing import override

from pygame_core.ecs.game_object import GameObject
from pygame_core.ecs.components.sprite_renderer2d import SpriteRenderer2D
from pygame_core.ecs.components.animator import Animator, AnimationClip
from pygame_core.sprite_sheet import SpriteSheet
from pygame_core.asset_path import ImagePath

from util.constants import *
from gameplay.animation import scaled_row
from gameplay.combat import find_nearest
from gameplay.ui import draw_radial_progress


class Flag(GameObject):
    """An objective marker that captures over time while held, and resists
    capture while a drone is nearby -- see FLAG_* constants in
    util/constants.py. Game._check_end_conditions() declares VICTORY once
    every Flag on the map is captured."""

    def __init__(self, game, position):
        super().__init__(name="flag")
        self.game = game

        self.rect.size = (FLAG_SIZE * SCALE_FACTOR, FLAG_SIZE * SCALE_FACTOR)
        self.rect.center = position

        self.add_component(SpriteRenderer2D)
        animator = self.add_component(Animator)
        frames = scaled_row(SpriteSheet.from_path(ImagePath("objective-flag", "ui")), 0, 6, FLAG_SIZE)
        animator.add_clip("default", AnimationClip(frames, fps=6.0, loop=True))
        animator.play("default")

        self.pulse_frames = scaled_row(SpriteSheet.from_path(ImagePath("objective-pulse", "ui")), 0, 6, FLAG_SIZE)
        self.pulse_frame = 0

        self.progress = 0.0
        self.captured = False

        game.all_sprites.append(self)
        game.flags.append(self)

    def _holders(self):
        return [self.game.player] + [s for s in self.game.soldiers if s.is_in_army]

    def is_held(self) -> bool:
        return find_nearest(Vector2(self.rect.center), self._holders(), FLAG_CAPTURE_RADIUS) is not None

    def is_contested(self) -> bool:
        return find_nearest(Vector2(self.rect.center), self.game.robots, FLAG_CONTEST_RADIUS) is not None

    @override
    def update(self) -> None:
        super().update()
        if self.captured:
            return

        if self.is_contested():
            self.progress = max(0.0, self.progress - FLAG_DECAY_RATE * self.game.delta_time)
        elif self.is_held():
            self.progress = min(100.0, self.progress + FLAG_CAPTURE_RATE * self.game.delta_time)
            if self.progress >= 100.0:
                self.captured = True

    def draw_pulse(self, surface, camera) -> None:
        if self.captured:
            return

        # Capture fill drawn first so it sits behind both the pulse ring
        # and the flag's own sprite (rendered later in Game.draw()'s main
        # sprite loop) -- a background disc growing behind the flag, not a
        # bar floating above it.
        self._draw_capture_progress(surface, camera)

        self.pulse_frame = (self.pulse_frame + 1) % (len(self.pulse_frames) * 10)
        image = self.pulse_frames[self.pulse_frame // 10]
        topleft = camera.world_to_screen(self.rect.topleft)
        surface.blit(camera.scale_image(image), (topleft.x, topleft.y))

    def _draw_capture_progress(self, surface, camera) -> None:
        if self.progress <= 0.0:
            return
        draw_radial_progress(surface, camera, self.rect.center,
                             FLAG_CAPTURE_ELLIPSE_RX, FLAG_CAPTURE_ELLIPSE_RY,
                             self.progress / 100.0, (80, 220, 80),
                             alpha=FLAG_CAPTURE_FILL_ALPHA)
