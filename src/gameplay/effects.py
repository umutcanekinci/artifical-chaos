import pygame
from pygame.math import Vector2
from typing import override

from pygame_core.ecs.game_object import GameObject
from pygame_core.ecs.components.sprite_renderer2d import SpriteRenderer2D
from pygame_core.ecs.components.animator import Animator
from pygame_core.sprite_sheet import SpriteSheet
from pygame_core.image import scale_by
from pygame_core.asset_path import AssetPath

from util.constants import *
from gameplay.animation import add_oneshot_clip


class TimedEffect(GameObject):
    """A one-shot sprite-sheet animation that removes itself once its clip
    finishes playing -- muzzle flashes, hit sparks/spatters, explosions.
    Purely cosmetic: spawned by attack()/die() call sites, never touched by
    gameplay/combat.py, so combat logic stays testable without a real
    Animator/renderer."""

    def __init__(self, game, position, path, row: int, frame_count: int, *,
                size: int, fps: float, facing: int = 0, name: str = "play") -> None:
        super().__init__(name=name)
        self.rect.size = (size * SCALE_FACTOR, size * SCALE_FACTOR)
        self.rect.center = position

        self.add_component(SpriteRenderer2D)
        self.add_component(Animator)
        add_oneshot_clip(self, path, row, frame_count, name=name, size=size, fps=fps)
        self.get_component(Animator).play(f"{name}_{facing}")

        game.all_sprites.append(self)

    @override
    def update(self) -> None:
        super().update()
        if not self.get_component(Animator).is_playing:
            self.active = False


class MuzzleFlash(TimedEffect):
    def __init__(self, game, position, facing: int = 0) -> None:
        super().__init__(game, position, AssetPath("muzzle-flashes", "Effects"),
                         row=0, frame_count=4, size=8, fps=MUZZLE_FLASH_FPS,
                         facing=facing, name="flash")


class HitSpark(TimedEffect):
    """Metal spark burst -- spawned where a drone takes a hit."""

    def __init__(self, game, position, facing: int = 0) -> None:
        super().__init__(game, position, AssetPath("hit-sparks", "Effects"),
                         row=0, frame_count=6, size=8, fps=HIT_SPARK_FPS,
                         facing=facing, name="spark")


class HitSpatter(TimedEffect):
    """Blood spatter -- spawned where the player or a soldier takes a hit."""

    def __init__(self, game, position, facing: int = 0) -> None:
        super().__init__(game, position, AssetPath("hit-spatters", "Effects"),
                         row=0, frame_count=6, size=8, fps=HIT_SPATTER_FPS,
                         facing=facing, name="spatter")


class Explosion(TimedEffect):
    """Drone destruction burst."""

    def __init__(self, game, position, facing: int = 0) -> None:
        super().__init__(game, position, AssetPath("small-explosion", "Effects"),
                         row=0, frame_count=9, size=24, fps=EXPLOSION_FPS,
                         facing=facing, name="boom")


class Tracer(GameObject):
    """A short-lived visual-only "bullet" that flies from an attacker to its
    target over TRACER_DURATION_MS, then disappears. Purely cosmetic on top
    of the already-instant hitscan hit resolution (gameplay/combat.py) --
    damage is already applied by the time this spawns; it never gates
    anything and doesn't rotate to face travel direction (frame 0 of
    bullets+plasma.png is a small non-directional dot, not an elongated
    bullet, so rotation wouldn't read as different anyway)."""

    def __init__(self, game, start, end) -> None:
        super().__init__(name="tracer")
        self.start = Vector2(start)
        self.end = Vector2(end)
        self.spawn_time = pygame.time.get_ticks()

        self.rect.size = (TRACER_SIZE * SCALE_FACTOR, TRACER_SIZE * SCALE_FACTOR)
        self.rect.center = self.start

        renderer = self.add_component(SpriteRenderer2D)
        sheet = SpriteSheet.from_path(AssetPath("bullets+plasma", "Projectiles"))
        renderer.set_image(scale_by(sheet.frame(0, 0, TRACER_SIZE, TRACER_SIZE), SCALE_FACTOR))

        game.all_sprites.append(self)

    @override
    def update(self) -> None:
        elapsed = pygame.time.get_ticks() - self.spawn_time
        if elapsed >= TRACER_DURATION_MS:
            self.active = False
            return
        t = elapsed / TRACER_DURATION_MS
        self.rect.center = self.start.lerp(self.end, t)
        super().update()
