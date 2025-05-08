
import pygame
from scripts.animation_clip import AnimationClip
from scripts.components.animator import Animator
from scripts.components.rigidbody import RigidBody
from scripts.entity import Entity
from scripts.spritesheet import Spritesheet
from scripts.settings import *
from pygame.math import Vector2

class Soldier(Entity):

	PATH = "assets/images/soliders/Assault-Class.png"
	MAX_HP = 100
	RADIUS = 50

	def __init__(self, game, position):
		super().__init__(position, Soldier.MAX_HP, Soldier.PATH, game.allSprites)
		self.game = game
		self.lastFootprint = 0
		self.leftFoot = True
		self.isInArmy = False
		self.pickCollider = pygame.Rect(0, 0, self.RADIUS * SCALE_FACTOR, self.RADIUS * SCALE_FACTOR)
		self.pickCollider.center = self.position

	def IsInPickRange(self, position) -> bool:
		return self.pickCollider.collidepoint(position)

	def AddToArmy(self):
		self.isInArmy = True

	def Attack(self):

		print("Solider is attacking...")

	def Walk(self):

		if self.game.keys[pygame.K_a] or self.game.keys[pygame.K_LEFT]:
			self.facing = -1

		if self.game.keys[pygame.K_d] or self.game.keys[pygame.K_RIGHT]:
			self.facing = 1

		self.rotation = self.game.player.position - self.position

		if self.rotation.length() > 100:
			self.status = Soldier.AnimationState.WALKING
			self.acceleration = self.rotation.normalize() * self.MS
		else:
			self.acceleration = Vector2()
			self.status = Soldier.AnimationState.IDLE
		
	def AvoidEntities(self):
		for solider in self.game.soliders:
			if solider != self:
				dist = self.position - solider.position
				if 0 < dist.length() < AVOID_RADIUS:
					self.acceleration += dist.normalize()

	def update(self) -> None:
		if self.isInArmy:
			self.Walk()
			self.AvoidEntities()
		
		super().update(self.game.deltaTime)