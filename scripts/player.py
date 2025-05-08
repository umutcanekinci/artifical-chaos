from typing import Any
import pygame
from scripts.animation_clip import AnimationClip
from scripts.components.animator import Animator
from scripts.components.rigidbody import RigidBody
from scripts.entity import Entity
from scripts.settings import *
from scripts.path import *
from pygame.math import Vector2
from pygame.sprite import Sprite

from scripts.spritesheet import Spritesheet

class Footprint(Sprite):

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

class Player(Entity):
	PATH = "assets/images/soliders/SquadLeader.png"
	RANK_PATH = "assets/images/UI/squad-insignia.png"
	MAX_HP = 100
	RANK_POSITION = (0, RANK_SIZE * SCALE_FACTOR)
	
	def __init__(self, game, position):
		super().__init__(position, Player.MAX_HP, Player.PATH, game.allSprites)
		self.game = game
		self.lastFootprint = 0
		self.leftFoot = True
		self.rank = 0
		self.rankRect = pygame.Rect(0, 0, RANK_SIZE * SCALE_FACTOR, RANK_SIZE * SCALE_FACTOR)
		self.init_rank_image()

	def init_rank_image(self):
		self.rankSheet = Spritesheet(Player.RANK_PATH)
		self.UpdateRankImage()

	def GetRankImage(self) -> pygame.Surface:
		return self.rankSheet.GetImage(5+self.rank%6, self.rank//5, RANK_SIZE, RANK_SIZE)

	def UpdateRankImage(self):
		self.rankImage = self.GetRankImage()

	def Attack(self):
		print("Solider is attacking...")

	def TakeDamage(self, damage):
		self.hp -= damage

		if self.hp <= 0:
			self.Die()

	def Die(self):
		self.kill()

	def Promote(self):
		self.rank += 1
		self.rankImage = self.GetRankImage()

	def update(self) -> None:
		self.CollectSoldiers()
		self.UpdateRotation()
		self.Walk()
		
		super().update(self.game.deltaTime)

	def CollectSoldiers(self):
		for soldier in self.game.soliders:
			if (not soldier.IsInPickRange(self.rect.center)): #Vector2(solider.rect.center) - Vector2(self.rect.center)).length() < 50:
				continue
			
			soldier.AddToArmy()

	def UpdateRotation(self):
		if self.game.keys[pygame.K_w] or self.game.keys[pygame.K_UP]:
			self.rotation.y = -1
		elif self.game.keys[pygame.K_s] or self.game.keys[pygame.K_DOWN]:
			self.rotation.y = 1
		else:
			self.rotation.y = 0

		if self.game.keys[pygame.K_a] or self.game.keys[pygame.K_LEFT]:
			self.rotation.x = -1
			self.facing = -1
		elif self.game.keys[pygame.K_d] or self.game.keys[pygame.K_RIGHT]:
			self.rotation.x = 1
			self.facing = 1
		else:
			self.rotation.x = 0

	def Walk(self):
		isWalking = self.rotation.length() > 0
		if isWalking:
			self.status = Player.AnimationState.WALKING
			self.acceleration = self.rotation.normalize() * self.speed

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
			self.status = Player.AnimationState.IDLE
	
	def DrawRank(self, surface: pygame.Surface) -> None:		
		self.rankRect.center = self.position - Player.RANK_POSITION
		surface.blit(self.rankImage, self.game.camera.Apply(self.rankRect))
