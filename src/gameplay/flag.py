import random

import pygame
from pygame.math import Vector2
from typing import override

from pygamine.ecs.game_object import GameObject
from pygamine.ecs.components.sprite_renderer2d import SpriteRenderer2D
from pygamine.ecs.components.animator import Animator
from pygamine.ecs.components.animation_clip import AnimationClip
from pygamine.sprite_sheet import SpriteSheet
from pygamine.asset_path import ImagePath

from util.constants import *
from gameplay.animation import scaled_row
from gameplay.combat import find_nearest, ready_to_attack
from gameplay.robot import DRONE_CLASSES
from gameplay.ui import draw_radial_progress


class Flag(GameObject):
    """An objective marker that captures over time while held, and resists
    capture while a drone is nearby -- see FLAG_* constants in
    util/constants.py. Game._check_end_conditions() declares VICTORY once
    every Flag on the map is captured. While uncaptured, also keeps
    spawning reinforcement drones near itself on a cooldown (_spawn_drone())
    -- the original single guardian (Map.spawn_objects()) can die quickly,
    which used to leave nothing contesting the flag at all."""

    def __init__(self, game, position, tier=None):
        """`tier` is one of util/constants.py's FLAG_TIERS entries (or None,
        used by every test that constructs a Flag directly and by any flag
        Map.spawn_objects() couldn't rank -- falls back to the untiered
        defaults, same behavior as before tiers existed)."""
        super().__init__(name="flag")
        self.game = game
        self.tier = tier

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

        self.spawned_drones = []
        self.last_spawn_time = 0

        game.all_sprites.append(self)
        game.flags.append(self)

    def _holders(self):
        return [self.game.player] + [s for s in self.game.soldiers if s.is_in_army]

    def is_held(self) -> bool:
        return find_nearest(Vector2(self.rect.center), self._holders(), FLAG_CAPTURE_RADIUS) is not None

    def is_contested(self) -> bool:
        return find_nearest(Vector2(self.rect.center), self.game.robots, FLAG_CONTEST_RADIUS) is not None

    def _spawn_drone(self) -> None:
        """Spawns one more reinforcement drone near this flag, gated by
        FLAG_SPAWN_COOLDOWN_MS and capped at FLAG_SPAWN_MAX_CONCURRENT
        drones alive from this flag at once (tracked via self.spawned_drones,
        pruned of anything already dead/purged each call) -- so a flag can't
        flood the map with an unbounded pile of drones, just keep a steady
        trickle going for as long as it stays uncaptured."""
        now = pygame.time.get_ticks()
        if not ready_to_attack(now, self.last_spawn_time, FLAG_SPAWN_COOLDOWN_MS):
            return
        self.spawned_drones = [d for d in self.spawned_drones if d.active]
        max_concurrent = self.tier["spawn_max_concurrent"] if self.tier else FLAG_SPAWN_MAX_CONCURRENT
        if len(self.spawned_drones) >= max_concurrent:
            return
        self.last_spawn_time = now

        offset = Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        if offset.length() > 0:
            offset.scale_to_length(random.uniform(0, FLAG_SPAWN_RADIUS))
        pool = self.tier["drone_pool"] if self.tier else tuple(DRONE_CLASSES)
        drone_class = DRONE_CLASSES[random.choice(pool)]
        drone = drone_class(self.game, Vector2(self.rect.center) + offset)
        self.spawned_drones.append(drone)

    @override
    def update(self) -> None:
        super().update()
        if self.captured:
            return

        self._spawn_drone()

        if self.is_contested():
            self.progress = max(0.0, self.progress - FLAG_DECAY_RATE * self.game.delta_time)
        elif self.is_held():
            self.progress = min(100.0, self.progress + FLAG_CAPTURE_RATE * self.game.delta_time)
            if self.progress >= 100.0:
                self.captured = True
                self.game.player.rank_up()

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
