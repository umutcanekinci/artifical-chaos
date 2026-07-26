import pygame
from pygame.math import Vector2
from typing import override

from pygame_core.ecs.game_object import GameObject
from pygame_core.ecs.components.sprite_renderer2d import SpriteRenderer2D
from pygame_core.ecs.components.animator import Animator
from pygame_core.asset_path import ImagePath

from util.constants import *
from gameplay.collision import collide
from gameplay.animation import add_directional_clips
from gameplay.combat import apply_damage, find_nearest, ready_to_attack


class Soldier(GameObject):
    """A recruitable ally. `soldier_class` looks up movement speed and
    fire stats from SOLDIER_CLASSES (util/constants.py) and picks the
    matching sprite sheet -- only classes that fit the existing
    single-target hitscan attack are wired up (Assault/Sniper/MachineGunner/
    AntiTank); Grenadier and RadioOperator need mechanics this codebase
    doesn't have yet (AoE, a support ability), see GDD.md."""

    def __init__(self, game, position, soldier_class: str = "Assault-Class"):
        super().__init__(name="soldier")
        self.game = game
        self.hp = 100
        stats = SOLDIER_CLASSES[soldier_class]
        self.ms = stats["speed"]
        self.fire_range = stats["fire_range"]
        self.fire_damage = stats["fire_damage"]
        self.fire_cooldown_ms = stats["fire_cooldown_ms"]

        self.acceleration = Vector2()
        self.velocity = Vector2()
        self.position = Vector2(position)
        self.rotation = Vector2()

        self.rect.size = (SPRITE_SIZE * SCALE_FACTOR, SPRITE_SIZE * SCALE_FACTOR)
        self.hit_rect = pygame.Rect(0, 0, SPRITE_SIZE * SCALE_FACTOR / 2, SPRITE_SIZE * SCALE_FACTOR / 2)
        self.rect.center = self.hit_rect.center = position

        self.status = "idle"
        self.facing = 0
        self.is_in_army = False
        self.last_attack_time = 0

        self.add_component(SpriteRenderer2D)
        self.add_component(Animator)
        add_directional_clips(self, ImagePath(soldier_class, "soliders"),
                              {"idle": 0, "walking": 1, "fire": 3})
        self.get_component(Animator).play("idle_0")

        game.all_sprites.append(self)
        game.soldiers.append(self)

    def add_to_army(self):
        self.is_in_army = True

    def walk(self):
        if self.game.keys[pygame.K_a] or self.game.keys[pygame.K_LEFT]:
            self.facing = 1
        if self.game.keys[pygame.K_d] or self.game.keys[pygame.K_RIGHT]:
            self.facing = 0

        self.rotation = self.game.player.position - self.position

        if self.rotation.length() > 100:
            self.status = "walking"
            self.acceleration = self.rotation.normalize() * self.ms
        else:
            self.acceleration = Vector2()
            self.status = "idle"

    def move(self):
        self.velocity = self.acceleration * self.game.delta_time * self.ms
        self.velocity -= self.velocity * FRICTION * self.game.delta_time
        self.position += self.velocity * self.game.delta_time

        self.rect.center = self.hit_rect.center = self.position

        self.hit_rect.centerx += self.velocity.x
        collide(self, 'x', self.game.walls)
        self.hit_rect.centery += self.velocity.y
        collide(self, 'y', self.game.walls)

    def avoid_entities(self):
        for soldier in self.game.soldiers:
            if soldier is not self:
                dist = self.position - soldier.position
                if 0 < dist.length() < AVOID_RADIUS:
                    self.acceleration += dist.normalize()

    def attack(self, target, damage: int, cooldown_ms: int) -> None:
        now = pygame.time.get_ticks()
        if not ready_to_attack(now, self.last_attack_time, cooldown_ms):
            return
        self.last_attack_time = now
        if apply_damage(target, damage):
            target.die()

    def engage(self) -> None:
        """Fights the nearest drone in range instead of following the
        player, if one's close enough; otherwise falls back to walk()."""
        target = find_nearest(self.position, self.game.robots, self.fire_range)
        if target is None:
            self.walk()
            return

        self.acceleration = Vector2()
        self.status = "fire"
        delta = target.position - self.position
        if abs(delta.x) > FACING_DEADZONE:
            self.facing = 1 if delta.x < 0 else 0
        self.attack(target, self.fire_damage, self.fire_cooldown_ms)

    @override
    def update(self):
        if self.is_in_army:
            self.engage()
            self.avoid_entities()
            self.move()

        self.get_component(Animator).play(f"{self.status}_{self.facing}")
        super().update()

    def die(self):
        self.active = False
