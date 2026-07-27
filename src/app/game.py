import pygame
from typing import override

from pygame_core.application import Application
from pygame_core.ecs.game_object_list import GameObjectList
from pygame_core.image import load_image
from pygame_core.asset_path import ImagePath

from util.constants import *
from gameplay.camera import FollowCamera
from gameplay.map import Map
from gameplay.player import Player


class Game(Application):

    def __init__(self):
        super().__init__(SIZE, "Artificial Chaos", FPS)

        self.all_sprites = GameObjectList()
        self.walls = GameObjectList()
        self.flags = GameObjectList()
        self.soldiers = GameObjectList()
        self.robots = GameObjectList()

        self.map = Map(self)
        self.camera = FollowCamera(pygame.Rect((0, 0), self.size),
                                   map_width=self.map.rect.width,
                                   map_height=self.map.rect.height)
        self.player = Player(self, self.map.rect.center)

        self.mouse.set_cursor_visible(False)
        self.cursor = load_image(ImagePath("mouse-pointer", "ui"))

        # Win/lose (see GDD.md): victory is holding every Flag until it's
        # captured (gameplay/flag.py) -- richer lose states beyond player
        # death are still deferred.
        self.game_over = False
        self.end_message = ""
        self._end_font = pygame.font.SysFont("Arial", 96, bold=True)

    @override
    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            self.player.toggle_squad_stance()

    @override
    def update(self):
        if self.game_over:
            return

        self.delta_time = self.clock.get_time() / 1000
        self.camera.follow(self.player.rect.center)
        self.all_sprites.update()
        self._purge_inactive()
        self._check_end_conditions()

    def _purge_inactive(self):
        for group in (self.all_sprites, self.walls, self.flags, self.soldiers, self.robots):
            group[:] = [obj for obj in group if obj.active]

    def _check_end_conditions(self) -> None:
        if self.player.is_dead:
            self.game_over = True
            self.end_message = "GAME OVER"
        elif self.flags and all(flag.captured for flag in self.flags):
            self.game_over = True
            self.end_message = "VICTORY"

    @override
    def draw(self):
        self.window.fill((0, 0, 0))

        map_pos = self.camera.world_to_screen((0, 0))
        self.window.blit(self.camera.scale_image(self.map.image), (map_pos.x, map_pos.y))

        for flag in self.flags:
            flag.draw_pulse(self.window, self.camera)

        for soldier in self.soldiers:
            soldier.draw_recruited_marker(self.window, self.camera)

        for obj in self.all_sprites:
            self.camera.draw(self.window, obj)

        for soldier in self.soldiers:
            soldier.draw_health(self.window, self.camera)
        for robot in self.robots:
            robot.draw_health(self.window, self.camera)

        self.player.draw_rank(self.window, self.camera)
        self.player.draw_health(self.window, self.camera)
        self.window.blit(self.cursor, self.mouse.position)

        if self.game_over:
            self._draw_end_message()

    def _draw_end_message(self) -> None:
        overlay = pygame.Surface(self.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.window.blit(overlay, (0, 0))

        text = self._end_font.render(self.end_message, True, (255, 255, 255))
        rect = text.get_rect(center=(self.size[0] // 2, self.size[1] // 2))
        self.window.blit(text, rect)

    @override
    def draw_debug(self):
        self.map.draw_grid(self.window, self.camera)
        for obj in self.all_sprites:
            self._draw_rect(obj.rect)
        for wall in self.walls:
            self._draw_rect(wall.rect)
        self._draw_rect(self.player.hit_rect)

    def _draw_rect(self, rect):
        topleft = self.camera.world_to_screen(rect.topleft)
        size = (self.camera.scaled(rect.width), self.camera.scaled(rect.height))
        pygame.draw.rect(self.window, (255, 0, 0), pygame.Rect(topleft, size), 1)
