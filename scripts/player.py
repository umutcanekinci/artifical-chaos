from typing import Any
import pygame
from scripts.settings import *
from scripts.path import *
from pygame.math import Vector2
from scripts.spritesheet import Spritesheet, Collide
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
		self.MS = 100
		self.rank = 0
		self.acceleration = Vector2()
		self.velocity = Vector2()
		self.position = Vector2(position)

		self.rotation = Vector2()

		self.rect = pygame.Rect(0, 0, SPRITE_SIZE * SCALE_FACTOR, SPRITE_SIZE * SCALE_FACTOR)
		self.hitRect = pygame.Rect(0, 0, SPRITE_SIZE * SCALE_FACTOR / 2, SPRITE_SIZE * SCALE_FACTOR / 2)
		self.rect.center = self.hitRect.center = position

		self.status = "idle"
		self.counter = 0
		self._LoadImages()

		self.lastFootprint = 0
		self.facing = 0
		self.leftFoot = True
		self.rankPosition = (0, RANK_SIZE * SCALE_FACTOR)
		self.rankRect = pygame.Rect(0, 0, RANK_SIZE * SCALE_FACTOR, RANK_SIZE * SCALE_FACTOR)
		self._InitRankImage()

	def _LoadImages(self):
		
		self.sheet = Spritesheet("assets/images/soliders/SquadLeader.png")
		self.idle = [[self.sheet.GetImage(i, 0, SPRITE_SIZE, SPRITE_SIZE) for i in range(2)], [pygame.transform.flip(self.sheet.GetImage(i, 0, SPRITE_SIZE, SPRITE_SIZE), 1, 0) for i in range(2)]]
		self.walking = [[self.sheet.GetImage(i, 1, SPRITE_SIZE, SPRITE_SIZE) for i in range(2)], [pygame.transform.flip(self.sheet.GetImage(i, 1, SPRITE_SIZE, SPRITE_SIZE), 1, 0) for i in range(2)]]

		#crawl, fire, hit, death, throw.

	def _InitRankImage(self):

		self.rankSheet = Spritesheet("assets/images/UI/squad-insignia.png")
		self.rankImage = self.GetRankImage()

	def GetRankImage(self) -> pygame.Surface:

		return	self.rankSheet.GetImage(5+self.rank%6, self.rank//5, RANK_SIZE, RANK_SIZE)

	def UpdateRankImage(self):

		self.rankImage = self.GetRankImage()

	def Attack(self):

		print("Solider is attacking...")

	def TakeDamage(self, damage):

		self.hp -= damage

		if self.hp <= 0:
			self.Die()

	def Walk(self):

		if self.game.keys[pygame.K_w] or self.game.keys[pygame.K_UP]:

			self.rotation.y = -1

		elif self.game.keys[pygame.K_s] or self.game.keys[pygame.K_DOWN]:

			self.rotation.y = 1

		else:

			self.rotation.y = 0

		if self.game.keys[pygame.K_a] or self.game.keys[pygame.K_LEFT]:

			self.rotation.x = -1
			self.facing = 1

		elif self.game.keys[pygame.K_d] or self.game.keys[pygame.K_RIGHT]:

			self.rotation.x = 1
			self.facing = 0

		else:

			self.rotation.x = 0

		if self.rotation.length() > 0:

			self.status = "walking"
			self.acceleration = self.rotation.normalize() * self.MS

			if pygame.time.get_ticks() - self.lastFootprint >= FOOTPRINT_DURATION:
				
				if self.leftFoot:
					
					Footprint(self.game, Vector2(self.rect.center) + Vector2(20, 30))
					self.leftFoot = False

				else:
					
					Footprint(self.game, Vector2(self.rect.center) + Vector2(15, 30))
					self.leftFoot = True

				self.lastFootprint = pygame.time.get_ticks()
			
		else:
			
			self.acceleration = Vector2()
			self.status = "idle"

	def Move(self):

		self.velocity = self.acceleration * self.game.deltaTime * self.MS # Acceleration
		self.velocity -= self.velocity * FRICTION # Friction
		self.position += self.velocity * self.game.deltaTime

		self.rect.center = self.hitRect.center = self.position
		
		self.hitRect.centerx += self.velocity.x
		Collide(self, 'x', self.game.walls)
		self.hitRect.centery += self.velocity.y
		Collide(self, 'y', self.game.walls)
		""
	
	def PlayAnimation(self, images, speed):

		self.counter += speed

		if self.counter >= len(images):

			self.counter = 0

		self.image = images[int(self.counter)]

	def GetSolider(self):

		for solider in self.game.soliders:

			if (Vector2(solider.rect.center) - Vector2(self.rect.center)).length() < 50:

				solider.AddToArmy()
				self.rank 

	def RankUp(self):

		self.rank += 1
		self.rankImage = self.GetRankImage()

	def update(self, *args: Any, **kwargs: Any) -> None:

		self.GetSolider()

		self.Walk()

		self.Move()

		self.PlayAnimation(getattr(self, self.status)[self.facing], 0.1)

	def Die(self):

		self.kill()

	def DrawRank(self, surface: pygame.Surface) -> None:
		
		self.rankRect.center = self.position - self.rankPosition
		surface.blit(self.rankImage, self.game.camera.Apply(self.rankRect))
