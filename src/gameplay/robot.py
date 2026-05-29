import pygame
from typing import override

from pygame_core.ecs.game_object import GameObject
from pygame_core.ecs.components.sprite_renderer2d import SpriteRenderer2D
from pygame_core.ecs.components.animator import Animator
from pygame_core.asset_path import ImagePath

from util.constants import *
from gameplay.animation import add_directional_clips


class Scarab(GameObject):

    def __init__(self, game, position) -> None:
        super().__init__(name="scarab")
        self.game = game

        self.rect.size = (SPRITE_SIZE * SCALE_FACTOR, SPRITE_SIZE * SCALE_FACTOR)
        self.hit_rect = pygame.Rect(0, 0, SPRITE_SIZE * SCALE_FACTOR / 2, SPRITE_SIZE * SCALE_FACTOR / 2)
        self.rect.center = self.hit_rect.center = position
        self.face = 0

        self.add_component(SpriteRenderer2D)
        self.add_component(Animator)
        add_directional_clips(self, ImagePath("Scarab", "robots"), {"idle": 0, "walking": 1})
        self.get_component(Animator).play("idle_0")

        game.all_sprites.append(self)
        game.robots.append(self)

    @override
    def update(self) -> None:
        self.get_component(Animator).play(f"idle_{self.face}")
        super().update()
