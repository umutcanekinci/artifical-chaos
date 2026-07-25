import pygame
from pygame.math import Vector2
from typing import override

from pygame_core.ecs.game_object import GameObject
from pygame_core.ecs.components.sprite_renderer2d import SpriteRenderer2D
from pygame_core.ecs.components.animator import Animator
from pygame_core.asset_path import ImagePath

from util.constants import *
from gameplay.collision import collide
from gameplay.animation import add_directional_clips, add_death_clip
from gameplay.combat import apply_damage, find_nearest, ready_to_attack


class Scarab(GameObject):
    """A basic drone: idle until something enters AGGRO_RADIUS, then chases
    the nearest player/in-army-soldier, melees at point-blank range or fires
    at mid-range, and holds a destroyed frame for DESTROYED_DURATION_MS
    before being purged (see Game._purge_inactive)."""

    def __init__(self, game, position) -> None:
        super().__init__(name="scarab")
        self.game = game
        self.hp = SCARAB_HP
        self.ms = SCARAB_SPEED

        self.acceleration = Vector2()
        self.velocity = Vector2()
        self.position = Vector2(position)

        self.rect.size = (SPRITE_SIZE * SCALE_FACTOR, SPRITE_SIZE * SCALE_FACTOR)
        self.hit_rect = pygame.Rect(0, 0, SPRITE_SIZE * SCALE_FACTOR / 2, SPRITE_SIZE * SCALE_FACTOR / 2)
        self.rect.center = self.hit_rect.center = position

        self.status = "idle"
        self.facing = 0
        self.last_attack_time = 0
        self.death_time = 0

        self.add_component(SpriteRenderer2D)
        self.add_component(Animator)
        add_directional_clips(self, ImagePath("Scarab", "robots"),
                              {"idle": 0, "walking": 1, "fire": 2, "melee": 3})
        add_death_clip(self, ImagePath("Scarab", "robots"), row=4)
        self.get_component(Animator).play("idle_0")

        game.all_sprites.append(self)
        game.robots.append(self)

    def get_target(self):
        candidates = [self.game.player] + [s for s in self.game.soldiers if s.is_in_army]
        return find_nearest(self.position, candidates, AGGRO_RADIUS)

    def engage(self) -> None:
        target = self.get_target()
        if target is None:
            self.acceleration = Vector2()
            self.status = "idle"
            return

        delta = Vector2(target.position) - self.position
        distance = delta.length()

        if distance <= MELEE_RANGE:
            self.acceleration = Vector2()
            self.status = "melee"
            self.attack(target, MELEE_DAMAGE, MELEE_COOLDOWN_MS)
        elif distance <= FIRE_RANGE:
            self.acceleration = Vector2()
            self.status = "fire"
            self.attack(target, FIRE_DAMAGE, FIRE_COOLDOWN_MS)
        else:
            self.status = "walking"
            self.acceleration = delta.normalize() * self.ms

        if delta.x != 0:
            self.facing = 1 if delta.x < 0 else 0

    def attack(self, target, damage: int, cooldown_ms: int) -> None:
        now = pygame.time.get_ticks()
        if not ready_to_attack(now, self.last_attack_time, cooldown_ms):
            return
        self.last_attack_time = now
        if apply_damage(target, damage):
            target.die()

    def move(self) -> None:
        self.velocity = self.acceleration * self.game.delta_time * self.ms
        self.velocity -= self.velocity * FRICTION
        self.position += self.velocity * self.game.delta_time

        self.rect.center = self.hit_rect.center = self.position

        self.hit_rect.centerx += self.velocity.x
        collide(self, 'x', self.game.walls)
        self.hit_rect.centery += self.velocity.y
        collide(self, 'y', self.game.walls)

    def die(self) -> None:
        if self.status == "destroyed":
            return
        self.status = "destroyed"
        self.death_time = pygame.time.get_ticks()
        self.acceleration = Vector2()
        self.velocity = Vector2()

    @override
    def update(self) -> None:
        if self.status == "destroyed":
            if pygame.time.get_ticks() - self.death_time >= DESTROYED_DURATION_MS:
                self.active = False
        else:
            self.engage()
            self.move()

        self.get_component(Animator).play(f"{self.status}_{self.facing}")
        super().update()
