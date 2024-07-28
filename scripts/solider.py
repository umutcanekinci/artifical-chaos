
import pygame
from scripts.spritesheet import Spritesheet
from scripts.settings import *
from pygame.math import Vector2
from scripts.spritesheet import Collide

class Solider(pygame.sprite.Sprite):

	def __init__(self, game, position):
		
		super().__init__(game.allSprites, game.soliders)
		self.game = game
		self.HP = 100
		self.MS = 80

		self.acceleration = Vector2()
		self.velocity = Vector2()
		self.position = Vector2(position)

		self.rect = pygame.Rect(0, 0, SPRITE_SIZE * SCALE_FACTOR, SPRITE_SIZE * SCALE_FACTOR)
		self.hitRect = pygame.Rect(0, 0, SPRITE_SIZE * SCALE_FACTOR / 2, SPRITE_SIZE * SCALE_FACTOR / 2)
		self.rect.center = self.hitRect.center = position

		self.status = "idle"
		self.counter = 0
		self._LoadImages()

		self.lastFootprint = 0
		self.facing = 0
		self.leftFoot = True
		self.isInArmy = False

	def AddToArmy(self):

		self.isInArmy = True

	def _LoadImages(self):
		
		self.sheet = Spritesheet("assets/images/soliders/Assault-Class.png")
		self.idle = [[self.sheet.GetImage(i, 0, SPRITE_SIZE, SPRITE_SIZE) for i in range(2)], [pygame.transform.flip(self.sheet.GetImage(i, 0, SPRITE_SIZE, SPRITE_SIZE), 1, 0) for i in range(2)]]
		self.walking = [[self.sheet.GetImage(i, 1, SPRITE_SIZE, SPRITE_SIZE) for i in range(2)], [pygame.transform.flip(self.sheet.GetImage(i, 1, SPRITE_SIZE, SPRITE_SIZE), 1, 0) for i in range(2)]]

		#crawl, fire, hit, death, throw.

	def Attack(self):

		print("Solider is attacking...")

	def TakeDamage(self, damage):

		self.hp -= damage

		if self.hp <= 0:

			self.Die()

	def Walk(self):

		if self.game.keys[pygame.K_a] or self.game.keys[pygame.K_LEFT]:

			self.facing = 1

		if self.game.keys[pygame.K_d] or self.game.keys[pygame.K_RIGHT]:

			self.facing = 0

		self.rotation = self.game.player.position - self.position

		if self.rotation.length() > 100:

			self.status = "walking"
			self.acceleration = self.rotation.normalize() * self.MS

		else:

			self.acceleration = Vector2()
			self.status = "idle"


	def Move(self):

		self.velocity = self.acceleration * self.game.deltaTime * self.MS # Acceleration
		self.velocity -= self.velocity * FRICTION * self.game.deltaTime # Friction
		self.position += self.velocity * self.game.deltaTime

		self.rect.center = self.hitRect.center = self.position

		self.hitRect.centerx += self.velocity.x
		Collide(self, 'x', self.game.walls)
		self.hitRect.centery += self.velocity.y
		Collide(self, 'y', self.game.walls)
		

	def AvoidEntities(self):

		for solider in self.game.soliders:

			if solider != self:

				dist = self.position - solider.position

				if 0 < dist.length() < AVOID_RADIUS:

					self.acceleration += dist.normalize()

	def PlayAnimation(self, images, speed):

		self.counter += speed

		if self.counter >= len(images):

			self.counter = 0

		self.image = images[int(self.counter)]

	def update(self, *args, **kwargs) -> None:

		#self.Walk()

		if self.isInArmy:

			self.Walk()
			self.AvoidEntities()
			self.Move()
			
		self.PlayAnimation(getattr(self, self.status)[self.facing], 0.1)
		return super().update(*args, **kwargs)

	def Die(self):

		self.kill()