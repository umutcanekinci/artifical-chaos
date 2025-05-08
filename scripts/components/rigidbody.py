
from typing import Any
from pygame.math import Vector2

from scripts.settings import FRICTION
from scripts.spritesheet import Collide

class RigidBody:

    def __init__(self, position, size, mass=1.0):
        self.mass = mass
        self.size = size
        self.speed = 100
        self.facing = 1
        self.position = Vector2(position)
        self.velocity = Vector2()
        self.acceleration = Vector2()
        self.rotation = Vector2()

    def update(self, delta_time) -> None:
        self.move(delta_time)

    def move(self, delta_time):
        self.velocity = self.acceleration * delta_time * self.speed
        self.velocity -= self.velocity * FRICTION
        self.position += self.velocity * delta_time

        self.rect.center = self.hitRect.center = self.position

        self.hitRect.centerx += self.velocity.x
        Collide(self, 'x', self.game.walls)
        self.hitRect.centery += self.velocity.y
        Collide(self, 'y', self.game.walls)