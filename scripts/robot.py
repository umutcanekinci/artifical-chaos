import pygame
from scripts.spritesheet import Spritesheet
from scripts.settings import *

class Scarab(pygame.sprite.Sprite):

	def __init__(self, game, position) -> None:

		super().__init__(game.allSprites, game.robots)

		self.game = game

		self.spritesheet = Spritesheet("assets/images/robots/Scarab.png")
		self.idle = [[self.spritesheet.GetImage(i, 0, SPRITE_SIZE, SPRITE_SIZE) for i in range(2)], [pygame.transform.flip(self.spritesheet.GetImage(i, 0, SPRITE_SIZE, SPRITE_SIZE), 1, 0) for i in range(2)]]
		self.walking = [[self.spritesheet.GetImage(i, 1, SPRITE_SIZE, SPRITE_SIZE) for i in range(2)], [pygame.transform.flip(self.spritesheet.GetImage(i, 1, SPRITE_SIZE, SPRITE_SIZE), 1, 0) for i in range(2)]]

		self.rect = pygame.Rect(0, 0, SPRITE_SIZE * SCALE_FACTOR, SPRITE_SIZE * SCALE_FACTOR)
		self.hitRect = pygame.Rect(0, 0, SPRITE_SIZE * SCALE_FACTOR / 2, SPRITE_SIZE * SCALE_FACTOR / 2)
		self.rect.center = self.hitRect.center = position
		self.counter = 0
		self.face = 0

	def PlayAnimation(self, images, speed):

			self.counter += speed

			if self.counter >= len(images):

				self.counter = 0

			self.image = images[int(self.counter)]

	def update(self, *args, **kwargs) -> None:

		self.PlayAnimation(self.idle[self.face], 0.1)
		return super().update(*args, **kwargs)