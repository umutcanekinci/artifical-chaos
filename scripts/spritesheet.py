import pygame
from scripts.settings import *

class Spritesheet():

	def __init__(self, path):

		self.sheet = pygame.image.load(path)

	def GetImage(self, x, y, width, height):

		image = pygame.Surface((width, height), pygame.SRCALPHA)
		image.blit(self.sheet, (0, 0), (x*width, y*height, width, height))
		image = pygame.transform.scale_by(image, SCALE_FACTOR)
		return image

def isCollide(one, two):

	return one.hitRect.colliderect(two.rect)

def Collide(object, direction: str, spriteGroup: pygame.sprite.Group) -> None:

	hits = pygame.sprite.spritecollide(object, spriteGroup, False, isCollide)

	if hits and hits[0] != object:
		
		if direction == 'x':
			
			if object.hitRect.x < hits[0].rect.x: #object.delta.x > 0:
				
				object.hitRect.right = hits[0].rect.left - .1

			else:

				object.hitRect.left = hits[0].rect.right + .1

			object.velocity.x = 0

		if direction == 'y':

			if object.hitRect.y < hits[0].rect.y: #object.delta.y > 0:
				
				object.hitRect.bottom = hits[0].rect.top - .1
			
			else:
				
				object.hitRect.top = hits[0].rect.bottom + .1

			object.velocity.y = 0
