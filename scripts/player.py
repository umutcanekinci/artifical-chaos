from typing import Any
import pygame
from scripts.settings import *
from scripts.path import *
from pygame.math import Vector2
from scripts.map import Collide

class Spritesheet():

	def __init__(self, path):

		self.sheet = pygame.image.load(path)

	def GetImage(self, x, y, width, height):

		image = pygame.Surface((width, height), pygame.SRCALPHA)
		image.blit(self.sheet, (0, 0), (x*width, y*height, width, height))
		image = pygame.transform.scale_by(image, SCALE_FACTOR)
		return image

class Footprint(pygame.sprite.Sprite):

	def __init__(self, game, position):

		super().__init__(game.allSprites)

		self.game = game
		self.rect = pygame.Rect(0, 0, SPRITE_SIZE, SPRITE_SIZE)
		self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)
		self.size = 1
		pygame.draw.circle(self.image, (255, 255, 255), (SPRITE_SIZE//2, SPRITE_SIZE//2), self.size, 1)
		self.rect.center = position
		
		self.creationTime = pygame.time.get_ticks()

	def update(self, *args: Any, **kwargs: Any) -> None:

		if pygame.time.get_ticks() - self.creationTime >= FOOTPRINT_DURATION * 2:
			
			self.kill()

		else:

			self.size += 1
			self.image = pygame.Surface(self.rect.size, pygame.SRCALPHA)
			pygame.draw.circle(self.image, (255, 255, 255), (SPRITE_SIZE//2, SPRITE_SIZE//2), self.size//3, 1)

		return super().update(*args, **kwargs)

class Player(pygame.sprite.Sprite):

	def __init__(self, game, position):
		
		super().__init__(game.allSprites)
		self.game = game
		self.HP = 100
		self.MS = 2

		self.rect = pygame.Rect(0, 0, SPRITE_SIZE, SPRITE_SIZE)
		self.hitRect = pygame.Rect(0, 0, SPRITE_SIZE, SPRITE_SIZE)
		self.rect.center = position

		self.status = "idle"
		self.counter = 0
		self._LoadImages()


		self.lastFootprint = 0
		self.facing = 0
		self.leftFoot = True

	def _LoadImages(self):
		
		self.sheet = Spritesheet("assets/images/soliders/MachineGunner-Class.png")
		self.idle = [[self.sheet.GetImage(i, 0, *self.rect.size) for i in range(2)], [pygame.transform.flip(self.sheet.GetImage(i, 0, *self.rect.size), 1, 0) for i in range(2)]]
		self.walking = [[self.sheet.GetImage(i, 1, *self.rect.size) for i in range(2)], [pygame.transform.flip(self.sheet.GetImage(i, 1, *self.rect.size), 1, 0) for i in range(2)]]

		#crawl, fire, hit, death, throw.

	def Attack(self):

		print("Solider is attacking...")

	def TakeDamage(self, damage):

		self.hp -= damage

		if self.hp <= 0:
			self.Die()

	def Walk(self):

		self.rotation = Vector2(0, 0)

		if self.game.keys[pygame.K_w] or self.game.keys[pygame.K_UP]:

			self.rotation.y = -1

		if self.game.keys[pygame.K_s] or self.game.keys[pygame.K_DOWN]:

			self.rotation.y = 1

		if self.game.keys[pygame.K_a] or self.game.keys[pygame.K_LEFT]:

			self.rotation.x = -1
			self.facing = 1

		if self.game.keys[pygame.K_d] or self.game.keys[pygame.K_RIGHT]:

			self.rotation.x = 1
			self.facing = 0

		if self.rotation.length() > 0:

			self.status = "walking"
			self.rotation.normalize()
			velocity = self.rotation * self.MS

			if pygame.time.get_ticks() - self.lastFootprint >= FOOTPRINT_DURATION:
				
				if self.leftFoot:
					
					Footprint(self.game, Vector2(self.rect.center) + Vector2(20, 30))
					self.leftFoot = False

				else:
					
					Footprint(self.game, Vector2(self.rect.center) + Vector2(15, 30))
					self.leftFoot = True

				self.lastFootprint = pygame.time.get_ticks()

			self.rect.move_ip(velocity)
			self.hitRect.center = self.rect.center
			self.hitRect.centerx += velocity.x
			Collide(self, 'x', self.game.walls)
			self.hitRect.centery += velocity.y
			Collide(self, 'y', self.game.walls)

		else:

			self.status = "idle"


	def PlayAnimation(self, images, speed):

		self.counter += speed

		if self.counter >= len(images):

			self.counter = 0

		self.image = images[int(self.counter)]

	def update(self, *args: Any, **kwargs: Any) -> None:

		self.Walk()
		self.PlayAnimation(getattr(self, self.status)[self.facing], 0.1)
		return super().update(*args, **kwargs)

	def Die(self):

		self.kill()