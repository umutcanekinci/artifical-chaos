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


class Soldier(GameObject):

    def __init__(self, game, position):
        super().__init__(name="soldier")
        self.game = game
        self.hp = 100
        self.ms = 80

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

        self.add_component(SpriteRenderer2D)
        self.add_component(Animator)
        add_directional_clips(self, ImagePath("Assault-Class", "soliders"), {"idle": 0, "walking": 1})
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

    @override
    def update(self):
        if self.is_in_army:
            self.walk()
            self.avoid_entities()
            self.move()

        self.get_component(Animator).play(f"{self.status}_{self.facing}")
        super().update()

    def die(self):
        self.active = False
