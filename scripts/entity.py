from enum import Enum

import pygame

from scripts.animation_clip import AnimationClip
from scripts.components.animator import Animator
from scripts.components.health import Health
from scripts.components.rigidbody import RigidBody
from scripts.components.transform import Transform
from scripts.settings import SCALE_FACTOR, SPRITE_SIZE
from scripts.spritesheet import Spritesheet


class Entity(Transform, RigidBody, Animator, Health):
    
    class AnimationState(Enum):
        IDLE = 0
        WALKING = 1
        CRAWL = 2
        FIRE = 3
        HIT = 4
        DEATH = 5
        THROW = 6

    def __init__(self, position, max_hp=100, sprite_path=None, *args, **kwargs):
        self.sprite_path = sprite_path
        Transform.__init__(self, position, (SPRITE_SIZE * SCALE_FACTOR, SPRITE_SIZE * SCALE_FACTOR))
        RigidBody.__init__(self, position, (SPRITE_SIZE * SCALE_FACTOR, SPRITE_SIZE * SCALE_FACTOR), 1.0)
        Animator.__init__(self, args, kwargs)
        Health.__init__(self, max_hp)

        self.status = Entity.AnimationState.IDLE
        self.init_animator()

    def init_animator(self):
        sheet = Spritesheet(self.sprite_path)
        for y, state in enumerate(Entity.AnimationState):
            sprites         = [sheet.GetImage(i, y, SPRITE_SIZE, SPRITE_SIZE) for i in range(2)]
            reversedSprites = [pygame.transform.flip(sprites[i], 1, 0) for i in range(2)]

            animationClip = AnimationClip(state.name, 1, 120)
            reversedAnimationClip = AnimationClip(state.name + "_reversed", 1, 120)

            animationClip.load_frames(sprites)
            reversedAnimationClip.load_frames(reversedSprites)

            super().add_animation(animationClip)
            super().add_animation(reversedAnimationClip)

    def update(self, delta_time) -> None:
        animationName = self.status.name if self.facing == 1 else self.status.name + "_reversed"
        Animator.set_animation(self, animationName)

        RigidBody.update(self, delta_time)
        Animator.update(self, delta_time)