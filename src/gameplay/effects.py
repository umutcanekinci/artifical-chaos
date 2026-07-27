import pygame
from pygame.math import Vector2
from typing import override

from pygame_core.ecs.game_object import GameObject
from pygame_core.ecs.components.sprite_renderer2d import SpriteRenderer2D
from pygame_core.ecs.components.animator import Animator
from pygame_core.sprite_sheet import SpriteSheet
from pygame_core.image import scale_by
from pygame_core.asset_path import ImagePath

from util.constants import *
from gameplay.animation import add_directional_clips, add_oneshot_clip


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
        super().__init__(game, position, ImagePath("muzzle-flashes", "effects"),
                         row=0, frame_count=4, size=8, fps=MUZZLE_FLASH_FPS,
                         facing=facing, name="flash")


class LaserFlash(TimedEffect):
    """Energy-weapon muzzle flash -- a rounder, growing discharge burst
    instead of MuzzleFlash's gunpowder-style spark. Used for drone types
    whose DRONE_TYPES entry sets muzzle_effect: "laser" (Hornet, Wasp) --
    both are described as energy-based, not gunpowder, in GDD.md."""

    def __init__(self, game, position, facing: int = 0) -> None:
        super().__init__(game, position, ImagePath("laser-flash", "effects"),
                         row=0, frame_count=3, size=16, fps=LASER_FLASH_FPS,
                         facing=facing, name="laser")


class HitSpark(TimedEffect):
    """Metal spark burst -- spawned where a drone takes a hit."""

    def __init__(self, game, position, facing: int = 0) -> None:
        super().__init__(game, position, ImagePath("hit-sparks", "effects"),
                         row=0, frame_count=6, size=8, fps=HIT_SPARK_FPS,
                         facing=facing, name="spark")


class HitSpatter(TimedEffect):
    """Blood spatter -- spawned where the player or a soldier takes a hit."""

    def __init__(self, game, position, facing: int = 0) -> None:
        super().__init__(game, position, ImagePath("hit-spatters", "effects"),
                         row=0, frame_count=6, size=8, fps=HIT_SPATTER_FPS,
                         facing=facing, name="spatter")


class Explosion(TimedEffect):
    """Drone destruction burst."""

    def __init__(self, game, position, facing: int = 0) -> None:
        super().__init__(game, position, ImagePath("small-explosion", "effects"),
                         row=0, frame_count=9, size=24, fps=EXPLOSION_FPS,
                         facing=facing, name="boom")


class BigExplosion(TimedEffect):
    """Grenadier-Class splash-attack impact -- a bigger, visually distinct
    burst from Explosion (drone death) so a thrown grenade landing doesn't
    read as just another drone dying."""

    def __init__(self, game, position, facing: int = 0) -> None:
        super().__init__(game, position, ImagePath("big-explosion", "effects"),
                         row=0, frame_count=11, size=32, fps=BIG_EXPLOSION_FPS,
                         facing=facing, name="big_boom")


class Smoke(TimedEffect):
    """A lingering smoke puff, spawned alongside Explosion/BigExplosion at
    the same position and time -- SMOKE_FPS is deliberately slower than
    EXPLOSION_FPS/BIG_EXPLOSION_FPS, so smoke.png's own puff-and-disperse
    clip runs longer than either fireball and visibly outlasts it, reading
    as smoke lingering after the blast clears rather than a separate,
    independently-timed effect."""

    def __init__(self, game, position, facing: int = 0) -> None:
        super().__init__(game, position, ImagePath("smoke", "effects"),
                         row=0, frame_count=8, size=8, fps=SMOKE_FPS,
                         facing=facing, name="smoke")


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
        sheet = SpriteSheet.from_path(ImagePath("bullets+plasma", "projectiles"))
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


class Grenade(GameObject):
    """Tracer's lobbed counterpart for Grenadier-Class's splash attack: also
    a visual-only projectile over the already-applied instant hit (splash
    damage lands at throw time, see Soldier.attack()'s splash branch), but
    spins through Grenade.png's 8-frame tumble instead of holding one frame,
    and takes GRENADE_FLIGHT_MS (longer than TRACER_DURATION_MS) to cross
    the screen so it reads as thrown, not fired."""

    def __init__(self, game, start, end) -> None:
        super().__init__(name="grenade")
        self.start = Vector2(start)
        self.end = Vector2(end)
        self.spawn_time = pygame.time.get_ticks()

        self.rect.size = (GRENADE_SIZE * SCALE_FACTOR, GRENADE_SIZE * SCALE_FACTOR)
        self.rect.center = self.start

        self.add_component(SpriteRenderer2D)
        self.add_component(Animator)
        add_directional_clips(self, ImagePath("Grenade", "projectiles"), {"spin": 0},
                              frame_count=8, size=GRENADE_SIZE, fps=GRENADE_SPIN_FPS)
        self.get_component(Animator).play("spin_0")

        game.all_sprites.append(self)

    @override
    def update(self) -> None:
        elapsed = pygame.time.get_ticks() - self.spawn_time
        if elapsed >= GRENADE_FLIGHT_MS:
            self.active = False
            return
        t = elapsed / GRENADE_FLIGHT_MS
        self.rect.center = self.start.lerp(self.end, t)
        super().update()


class FloatingText(GameObject):
    """A short colored label that rises above `position` and fades out over
    FLOATING_TEXT_DURATION_MS -- used for rank-up stat feedback (Player.
    rank_up()), one instance per stat picked. `offset_index` nudges spawns
    sideways (see FLOATING_TEXT_X_SPACING) so two simultaneous picks don't
    render on top of each other."""

    _font: pygame.font.Font | None = None

    def __init__(self, game, position, text: str, color, offset_index: int = 0) -> None:
        super().__init__(name="floating_text")
        if FloatingText._font is None:
            FloatingText._font = pygame.font.SysFont("Arial", FLOATING_TEXT_FONT_SIZE, bold=True)

        self.start = Vector2(position) + Vector2(offset_index * FLOATING_TEXT_X_SPACING, 0)
        self.end = self.start - Vector2(0, FLOATING_TEXT_RISE_DISTANCE)
        self.spawn_time = pygame.time.get_ticks()

        self.image = FloatingText._font.render(text, True, color).convert_alpha()
        self.rect.size = self.image.get_size()
        self.rect.center = self.start

        renderer = self.add_component(SpriteRenderer2D)
        renderer.set_image(self.image)

        game.all_sprites.append(self)

    @override
    def update(self) -> None:
        elapsed = pygame.time.get_ticks() - self.spawn_time
        if elapsed >= FLOATING_TEXT_DURATION_MS:
            self.active = False
            return
        t = elapsed / FLOATING_TEXT_DURATION_MS
        self.rect.center = self.start.lerp(self.end, t)
        self.image.set_alpha(round(255 * (1.0 - t)))
        super().update()
