import pygame
from pytmx import load_pygame, TiledTileLayer
from scripts.settings import *

def isCollide(one, two):

	return one.hitRect.colliderect(two.rect)

def Collide(object, direction: str, spriteGroup: pygame.sprite.Group) -> None:

	hits = pygame.sprite.spritecollide(object, spriteGroup, False, isCollide)

	if hits and hits[0] != object:
		
		if direction == 'x':
			
			if object.rect.x < hits[0].rect.x: #object.delta.x > 0:
				
				object.hitRect.right = hits[0].rect.left - .001

			else:

				object.hitRect.left = hits[0].rect.right + .001

			object.velocity.x = 0

		if direction == 'y':

			if object.rect.y < hits[0].rect.y: #object.delta.y > 0:
				
				object.hitRect.bottom = hits[0].rect.top - .001
			
			else:
				
				object.hitRect.top = hits[0].rect.bottom + .001
			
			object.velocity.y = 0

class Camera():

	def __init__(self, size: tuple, map):
		
		self.rect = pygame.Rect((0, 0), size)
		self.map = map
		self.map.camera = self
		
	def Follow(self, targetRect):
		
		self.rect.x, self.rect.y = -targetRect.centerx + (self.rect.width / 2), -targetRect.centery + (self.rect.height / 2)
		
		self.rect.x = max(self.rect.width - self.map.rect.width, min(0, self.rect.x))
		self.rect.y = max(self.rect.height - self.map.rect.height, min(0, self.rect.y))

	def Apply(self, rect: pygame.Rect):
		
		return pygame.Rect((self.rect.x + rect.x, self.rect.y + rect.y), rect.size)

	def Draw(self, image, objects):

		if not hasattr(objects, '__iter__'):

			objects = [objects]

		for object in objects:
			
			image.blit(object.image, self.Apply(object.rect))

class Obstacle(pygame.sprite.Sprite):

	def __init__(self, game, position, size) -> None:
		
		self.game = game
		self.rect = pygame.Rect(position, size)
		super().__init__(game.walls, game.allSprites)
		self.image = pygame.Surface(self.rect.size)
		pygame.draw.rect(self.image, pygame.color.THECOLORS['yellow'], self.game.camera.Apply(self.rect), 2)


class Map(pygame.sprite.Sprite):

	def __init__(self, game):

		self.game = game
		super().__init__()
		
		self.tiledMap = load_pygame("assets/images/tileset/tiledmap.tmx")
		self.tileWidth, self.tileHeight = self.tiledMap.tilewidth * SCALE_FACTOR, self.tiledMap.tileheight * SCALE_FACTOR
		self.columnCount, self.rowCount = self.tiledMap.width, self.tiledMap.height

		self.Render()
		#self.DrawGrid()
		self.GetObjects()

	def Render(self):
		
		self.image = pygame.Surface((self.columnCount * self.tileWidth, self.rowCount * self.tileHeight), pygame.SRCALPHA)
		self.image.fill((255, 255, 255, 0))
		self.rect = self.image.get_rect()
		tileImage = self.tiledMap.get_tile_image_by_gid

		for layer in self.tiledMap.visible_layers:

			if isinstance(layer, TiledTileLayer):

				for x, y, gid in layer:

					tile = tileImage(gid)

					if tile:

						self.image.blit(pygame.transform.scale_by(tile, SCALE_FACTOR), (x * self.tileWidth, y * self.tileHeight))

	def GetObjects(self) -> None:

		for object in self.tiledMap.objects:

			#if "base" in object.name:

			#	self.basePoints[int(object.name[-1:])] = object.x + self.tileWidth / 2, object.y + self.tileHeight / 2

			if "spawnPoint" in object.name:

				self.spawnPoint = object.x + self.tileWidth / 2, object.y + self.tileHeight / 2

			if "wall" in object.name:

				Obstacle(self.game, (object.x, object.y), (object.width, object.height))

	def DrawGrid(self):

		# Draw column lines
		for columnNumber in range(self.columnCount+1):

			pygame.draw.line(self.image, pygame.color.THECOLORS['grey'], (columnNumber*self.tileWidth, 0), (columnNumber*self.tileWidth, self.rect.height), 1)

		# Draw row lines
		for rowNumber in range(self.rowCount+1):

			pygame.draw.line(self.image, pygame.color.THECOLORS['grey'], (0, rowNumber*self.tileHeight), (self.rect.width, rowNumber*self.tileHeight), 1)