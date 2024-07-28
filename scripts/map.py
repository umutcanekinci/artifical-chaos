import pygame
from pytmx import load_pygame, TiledTileLayer
from scripts.settings import *
from scripts.flag import Flag
from scripts.robot import Scarab
from scripts.solider import Solider

class Camera():

	def __init__(self, size: tuple, map):
		
		self.rect = pygame.Rect((0, 0), size)
		self.map = map
		self.map.camera = self
		
	def Follow(self, targetRect):
		
		self.rect.x, self.rect.y = -targetRect.centerx + (self.rect.width / 2), -targetRect.centery + (self.rect.height / 2)
		
		self.rect.x = max(self.rect.width - self.map.rect.width, min(0, self.rect.x))
		self.rect.y = max(self.rect.height - self.map.rect.height, min(0, self.rect.y))

	def Apply(self, rect: pygame.Rect) -> pygame.Rect:
		
		return pygame.Rect((self.rect.x + rect.x, self.rect.y + rect.y), rect.size)

	def Draw(self, image, objects):

		if not hasattr(objects, '__iter__'):

			objects = [objects]

		for object in objects:
			
			image.blit(object.image, self.Apply(object.rect))

class Obstacle(pygame.sprite.Sprite):

	def __init__(self, game, position, size) -> None:
		
		super().__init__(game.walls)

		self.game = game
		self.rect = pygame.Rect(position, size)

class Map(pygame.sprite.Sprite):

	def __init__(self, game):

		self.game = game
		super().__init__()
		
		self.tiledMap = load_pygame("assets/images/tileset/tiledmap.tmx")
		self.tileWidth, self.tileHeight = self.tiledMap.tilewidth * SCALE_FACTOR, self.tiledMap.tileheight * SCALE_FACTOR
		self.columnCount, self.rowCount = self.tiledMap.width, self.tiledMap.height

		self.GetObjects()
		self.Render()
		

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

			if "flag" in object.name:

				Flag(self.game, (object.x * SCALE_FACTOR + self.tileWidth / 2, object.y * SCALE_FACTOR + self.tileHeight / 2))
				Scarab(self.game, (object.x * SCALE_FACTOR + self.tileWidth / 2, object.y * SCALE_FACTOR + self.tileHeight / 2))
				Solider(self.game, (object.x * SCALE_FACTOR + self.tileWidth / 2, object.y * SCALE_FACTOR + self.tileHeight / 2 + 100))
			
			if "spawnPoint" in object.name:

				self.spawnPoint = object.x + self.tileWidth / 2, object.y + self.tileHeight / 2

			if "wall" in object.name:

				Obstacle(self.game, (object.x * SCALE_FACTOR, object.y * SCALE_FACTOR), (object.width * SCALE_FACTOR, object.height * SCALE_FACTOR))

	def DrawGrid(self, surface: pygame.Surface):
		
		# Draw column lines
		for columnNumber in range(self.columnCount+1):

			pygame.draw.line(surface, pygame.color.THECOLORS['grey'], (columnNumber*self.tileWidth + self.game.camera.rect.x, self.game.camera.rect.y), (columnNumber*self.tileWidth + self.game.camera.rect.x, self.rect.height + self.game.camera.rect.y), 1)

		# Draw row lines
		for rowNumber in range(self.rowCount+1):

			pygame.draw.line(surface, pygame.color.THECOLORS['grey'], (self.game.camera.rect.x, rowNumber*self.tileHeight + self.game.camera.rect.y), (self.rect.width + self.game.camera.rect.x, rowNumber*self.tileHeight + self.game.camera.rect.y), 1)