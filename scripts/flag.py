import pygame
from scripts.settings import *
from scripts.spritesheet import Spritesheet
from pygame.math import Vector2

class Flag(pygame.sprite.Sprite):

	def __init__(self, game, position):

		super().__init__(game.flags, game.allSprites)
		self.game = game
		self.rect = pygame.Rect(0, 0, FLAG_SIZE * SCALE_FACTOR, FLAG_SIZE * SCALE_FACTOR)
		self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)
		self.rect.center = position

		self.spritesheet = Spritesheet("assets/images/UI/objective-flag.png")
		self.pulseSpritesheet = Spritesheet("assets/images/UI/objective-pulse.png")

		self.animation = [self.spritesheet.GetImage(i, 0, FLAG_SIZE, FLAG_SIZE) for i in range(6)]
		self.frame = 0
		self.pulseFrame = 0

	def update(self, *args, **kwargs) -> None:

		self.image = self.animation[self.frame//10]

		if self.frame < len(self.animation) * 10 - 1:

			self.frame += 1

		else:
			
			self.frame = 0

		return super().update(*args, **kwargs)

	def DrawPulse(self, surface: pygame.Surface) -> None:

		if self.pulseFrame < len(self.animation) * 10 - 1:

			self.pulseFrame += 1

		else:
			
			self.pulseFrame = 0

		surface.blit(self.pulseSpritesheet.GetImage(self.pulseFrame//10, 0, FLAG_SIZE, FLAG_SIZE), self.game.camera.Apply(self.rect))

class Dot(pygame.sprite.Sprite):

	def __init__(self, game, position, destination):

		super().__init__(game.dots, game.allSprites)
		self.game = game

		self.spritesheet = Spritesheet("assets/images/UI/dotted-arrows.png")
		self.image = self.spritesheet.GetImage(0, 2, SPRITE_SIZE, SPRITE_SIZE)
		self.rect = self.image.get_rect(center = position)

		self.distance = Vector2(destination) - Vector2(self.rect.center)
		self.velocity = self.distance.normalize()

	def update(self, *args, **kwargs) -> None:

		#self.rect.center += self.velocity

		return super().update(*args, **kwargs)