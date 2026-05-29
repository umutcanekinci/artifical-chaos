from pygame_core.ecs.game_object import GameObject
from pygame_core.ecs.components.sprite_renderer2d import SpriteRenderer2D
from pygame_core.ecs.components.animator import Animator, AnimationClip
from pygame_core.sprite_sheet import SpriteSheet
from pygame_core.asset_path import ImagePath

from util.constants import *
from gameplay.animation import scaled_row


class Flag(GameObject):

    def __init__(self, game, position):
        super().__init__(name="flag")
        self.game = game

        self.rect.size = (FLAG_SIZE * SCALE_FACTOR, FLAG_SIZE * SCALE_FACTOR)
        self.rect.center = position

        self.add_component(SpriteRenderer2D)
        animator = self.add_component(Animator)
        frames = scaled_row(SpriteSheet.from_path(ImagePath("objective-flag", "UI")), 0, 6, FLAG_SIZE)
        animator.add_clip("default", AnimationClip(frames, fps=6.0, loop=True))
        animator.play("default")

        self.pulse_frames = scaled_row(SpriteSheet.from_path(ImagePath("objective-pulse", "UI")), 0, 6, FLAG_SIZE)
        self.pulse_frame = 0

        game.all_sprites.append(self)
        game.flags.append(self)

    def draw_pulse(self, surface, camera) -> None:
        self.pulse_frame = (self.pulse_frame + 1) % (len(self.pulse_frames) * 10)
        image = self.pulse_frames[self.pulse_frame // 10]
        topleft = camera.world_to_screen(self.rect.topleft)
        surface.blit(camera.scale_image(image), (topleft.x, topleft.y))
