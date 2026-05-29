import pygame

from pygame_core.tilemap import TiledMap
from pygame_core.ecs.game_object import GameObject
from pygame_core.asset_path import ImagePath

from util.constants import *
from gameplay.flag import Flag
from gameplay.robot import Scarab
from gameplay.soldier import Soldier


class Obstacle(GameObject):
    """Invisible collision wall — Transform only, no renderer."""

    def __init__(self, game, position, size) -> None:
        super().__init__(name="obstacle")
        self.rect.size = size
        self.rect.topleft = position
        game.walls.append(self)


class Map(TiledMap):
    """Tiled map for Artificial Chaos: pre-renders the tile layers scaled by
    SCALE_FACTOR and spawns world entities from the object layer."""

    def __init__(self, game):
        super().__init__(str(ImagePath("tiledmap", "tileset", "tmx")))
        self.game = game

        self.tile_width = self.tile_size * SCALE_FACTOR
        self.tile_height = self.tile_size * SCALE_FACTOR
        self.image = pygame.transform.scale_by(self.pre_render(alpha=True), SCALE_FACTOR)
        self.rect = self.image.get_rect()

        self.spawn_objects()

    def spawn_objects(self) -> None:
        for obj in self.tmx.objects:
            if "flag" in obj.name:
                Flag(self.game, (obj.x * SCALE_FACTOR + self.tile_width / 2, obj.y * SCALE_FACTOR + self.tile_height / 2))
                Scarab(self.game, (obj.x * SCALE_FACTOR + self.tile_width / 2, obj.y * SCALE_FACTOR + self.tile_height / 2))
                Soldier(self.game, (obj.x * SCALE_FACTOR + self.tile_width / 2, obj.y * SCALE_FACTOR + self.tile_height / 2 + 100))

            if "spawnPoint" in obj.name:
                self.spawn_point = obj.x + self.tile_width / 2, obj.y + self.tile_height / 2

            if "wall" in obj.name:
                Obstacle(self.game, (obj.x * SCALE_FACTOR, obj.y * SCALE_FACTOR), (obj.width * SCALE_FACTOR, obj.height * SCALE_FACTOR))

    def draw_grid(self, surface: pygame.Surface, camera):
        for column_number in range(self.cols + 1):
            x = column_number * self.tile_width
            start = camera.world_to_screen((x, 0))
            end = camera.world_to_screen((x, self.rect.height))
            pygame.draw.line(surface, pygame.color.THECOLORS['grey'], start, end, 1)

        for row_number in range(self.rows + 1):
            y = row_number * self.tile_height
            start = camera.world_to_screen((0, y))
            end = camera.world_to_screen((self.rect.width, y))
            pygame.draw.line(surface, pygame.color.THECOLORS['grey'], start, end, 1)
