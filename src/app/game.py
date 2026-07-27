import pygame
from typing import override

from pygame_core.application import Application
from pygame_core.ecs.game_object_list import GameObjectList
from pygame_core.image import load_image
from pygame_core.asset_path import ImagePath
from pygame_core.splash_screen import SplashScreen

from util.constants import *
from gameplay.camera import FollowCamera
from gameplay.map import Map
from gameplay.player import Player
from gameplay.tutorial import Tutorial

# Keys that must never double as "any key restarts the run" while the end
# screen is up -- Escape already quits (Application._handle_core_event,
# which always runs before Game's own handle_event()), and F1/F11 are
# meta/dev toggles (debug overlay, fullscreen) a player might still want to
# hit from the end screen without also kicking off a new run.
_RESTART_EXCLUDED_KEYS = frozenset({pygame.K_ESCAPE, pygame.K_F1, pygame.K_F11})


class Game(Application):

    def __init__(self):
        super().__init__(SIZE, "Artificial Chaos", FPS)

        self.mouse.set_cursor_visible(False)
        self.cursor = load_image(ImagePath("mouse-pointer", "ui"))

        self.splash = SplashScreen([ImagePath("pygame_logo", "branding"), ImagePath("title", "branding")],
                                   fade_ms=SPLASH_FADE_MS, hold_ms=SPLASH_HOLD_MS)

        self._end_font = pygame.font.SysFont("Arial", 96, bold=True)
        self._restart_font = pygame.font.SysFont("Arial", 36)
        self._any_key_icon = load_image(ImagePath("keyboard_any_outline", "input_prompts"), size=(96, 96))
        self._escape_icon = load_image(ImagePath("keyboard_escape_outline", "input_prompts"), size=(32, 32))
        # Generic mouse (no button highlighted) rather than mouse_left --
        # restart triggers on any mouse button, not specifically left click.
        self._mouse_icon = load_image(ImagePath("mouse_outline", "input_prompts"), size=(32, 32))

        self.restart()

    def restart(self) -> None:
        """(Re)builds everything that resets on a new attempt: entity
        lists, the map, player, and tutorial. Rebuilding the map reproduces
        the exact same layout every time -- flag/wall/RockObstacle
        placement all come from the tmx or a fixed seed, and flag-guardian
        drone/soldier class picks are a deterministic round-robin over
        tmx object order (see Map.spawn_objects()), not randomized -- so a
        restart is a clean identical do-over, not a reshuffled one. Called
        once from __init__ for the first run, and again by handle_event()
        on any key/click on the GAME OVER / VICTORY screen -- app-level
        one-time setup (cursor, splash, end-screen fonts) lives in
        __init__ instead, untouched by a restart."""
        self.all_sprites = GameObjectList()
        self.walls = GameObjectList()
        self.flags = GameObjectList()
        self.soldiers = GameObjectList()
        self.robots = GameObjectList()

        self.map = Map(self)
        self.camera = FollowCamera(pygame.Rect((0, 0), self.size),
                                   map_width=self.map.rect.width,
                                   map_height=self.map.rect.height)
        self.player = Player(self, self.map.spawn_point)
        self.tutorial = Tutorial(self)

        # Win/lose (see GDD.md): victory is holding every Flag until it's
        # captured (gameplay/flag.py) -- richer lose states beyond player
        # death are still deferred.
        self.game_over = False
        self.end_message = ""

    def run(self):
        # SplashScreen runs its own loop with direct pygame.display.update()
        # calls, bypassing Application._present()'s scale step -- draw it
        # straight onto the real display surface rather than the offscreen
        # logical canvas, or it would never actually reach the screen.
        self.splash.run(self.display_surface, self.clock, self._fps)
        super().run()

    @override
    def handle_event(self, event) -> None:
        if self.game_over:
            is_restart_key = event.type == pygame.KEYDOWN and event.key not in _RESTART_EXCLUDED_KEYS
            is_restart_click = event.type == pygame.MOUSEBUTTONDOWN
            if is_restart_key or is_restart_click:
                self.restart()
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            self.player.toggle_squad_stance()

    @override
    def update(self):
        if self.game_over:
            return

        self.delta_time = self.clock.get_time() / 1000
        self.camera.follow(self.player.rect.center)
        self.all_sprites.update()
        self.tutorial.update()
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
        self.player.draw_squad_stance(self.window)
        self.window.blit(self.cursor, self.mouse.position)

        if self.game_over:
            self._draw_end_message()
        else:
            self.tutorial.draw(self.window)

    def _draw_end_message(self) -> None:
        overlay = pygame.Surface(self.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.window.blit(overlay, (0, 0))

        text = self._end_font.render(self.end_message, True, (255, 255, 255))
        rect = text.get_rect(center=(self.size[0] // 2, self.size[1] // 2))
        self.window.blit(text, rect)

        bottom = self._draw_icon_caption(self._any_key_icon, ("or ", self._mouse_icon, " to restart"),
                                         rect.bottom + 40)
        if self.end_message == "VICTORY":
            self._draw_prompt_line(self._escape_icon, "Press Esc to exit", bottom + 30)

    def _draw_icon_caption(self, icon: pygame.Surface, caption_parts, top: int) -> int:
        """Blits a big icon centered at `top` with a caption below it,
        returning the caption's bottom y so callers can stack another
        prompt right under it. The icon itself already shows what it means
        (e.g. Kenney's "ANY" key-cap art) -- the caption only needs to say
        what pressing it does, not repeat "press any key". `caption_parts`
        mixes strings (rendered as text) and icon surfaces (e.g. a mouse
        icon standing in for the word "click") laid out inline left-to-
        right, vertically centered against each other."""
        icon_rect = icon.get_rect(midtop=(self.size[0] // 2, top))
        self.window.blit(icon, icon_rect)

        caption = self._build_inline(caption_parts)
        caption_rect = caption.get_rect(midtop=(self.size[0] // 2, icon_rect.bottom + 8))
        self.window.blit(caption, caption_rect)
        return caption_rect.bottom

    def _build_inline(self, parts) -> pygame.Surface:
        """Composes a row of text/icon parts (see _draw_icon_caption) into
        one surface, each part vertically centered against the tallest."""
        pieces = [self._restart_font.render(p, True, (200, 200, 200)) if isinstance(p, str) else p
                 for p in parts]
        width = sum(p.get_width() for p in pieces)
        height = max(p.get_height() for p in pieces)
        line = pygame.Surface((width, height), pygame.SRCALPHA)
        x = 0
        for piece in pieces:
            line.blit(piece, (x, (height - piece.get_height()) // 2))
            x += piece.get_width()
        return line

    def _draw_prompt_line(self, icon: pygame.Surface, text: str, top: int) -> int:
        """Blits one icon + text prompt line centered at `top`, returning
        its bottom y so callers can stack another line right under it."""
        label = self._restart_font.render(text, True, (200, 200, 200))
        gap = 12
        line = pygame.Surface((icon.get_width() + gap + label.get_width(),
                               max(icon.get_height(), label.get_height())), pygame.SRCALPHA)
        line.blit(icon, (0, (line.get_height() - icon.get_height()) // 2))
        line.blit(label, (icon.get_width() + gap, (line.get_height() - label.get_height()) // 2))

        rect = line.get_rect(midtop=(self.size[0] // 2, top))
        self.window.blit(line, rect)
        return rect.bottom

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
