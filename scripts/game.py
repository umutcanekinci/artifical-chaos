import pygame
from scripts.map import Map, Camera
from scripts.player import Player
from scripts.settings import *
from sys import exit
from scripts.flag import Dot
from pygame.math import Vector2

class Game():

    def __init__(self):

        # INITIALIZATION
        pygame.init()
        
        # FPS
        self.clock = pygame.time.Clock()

        # SCREEN
        self.rect = pygame.Rect(0, 0, pygame.display.Info().current_w, pygame.display.Info().current_h)
        self.window = pygame.display.set_mode(self.rect.size, pygame.FULLSCREEN)
        
        # GAME
        self.debugMode = False
        
        self.allSprites = pygame.sprite.Group()
        self.walls = pygame.sprite.Group()
        self.flags = pygame.sprite.Group()
        self.soliders = pygame.sprite.Group()
        self.robots = pygame.sprite.Group()

        self.map = Map(self)
        self.camera = Camera(self.rect.size, self.map)
        self.player = Player(self, self.map.rect.center)

        self.SetCursorVisible(False)
        self.SetCursorImage(pygame.image.load("assets/images/UI/mouse-pointer.png"))

        self.lastDot = 0
        

    def SetCursorVisible(self, value=True) -> None:

        pygame.mouse.set_visible(value)

    def SetCursorImage(self, image) -> None:

        self.cursor = image

    def Start(self):

        self.isRunning = True

        while self.isRunning:

            self.deltaTime = self.clock.tick(FPS) / 1000
            self.mousePosition = pygame.mouse.get_pos()
            self.keys = pygame.key.get_pressed()

            self.HandleEvents()
            self.Update()
            self.Draw()

            pygame.display.update()

    def HandleEvents(self):

        for event in pygame.event.get():

            if event.type == pygame.QUIT:

                self.Exit()

            elif event.type == pygame.KEYDOWN:

                if event.key == pygame.K_ESCAPE:

                    self.Exit()

                elif event.key == pygame.K_F2:

                    self.debugMode = not self.debugMode

    def Update(self):
        
        self.camera.Follow(self.player.rect)
        self.allSprites.update()

    def Draw(self):

        self.window.fill((0, 0, 0))
        self.camera.Draw(self.window, self.map)
        
        for flag in self.flags:

            flag.DrawPulse(self.window)

        self.camera.Draw(self.window, self.allSprites)
        self.player.DrawRank(self.window)

        """
        self.nearestFlag = min(self.flags, key=lambda x: (Vector2(self.player.rect.center) - Vector2(x.rect.center)).length())
        nearestFlagDistance = Vector2(self.player.rect.center) - Vector2(self.nearestFlag.rect.center)

        # Calculate the direction vector from the player to the nearest flag
        if nearestFlagDistance.length() > 0:
        
            direction = nearestFlagDistance.normalize()

        # Calculate the total distance from the player to the nearest flag
        total_distance = int(nearestFlagDistance.length())

        # Determine the spacing between the dots
        dot_spacing = 300

        # Calculate the number of dots to draw
        num_dots = total_distance // dot_spacing

        # Draw the dots
        for i in range(num_dots):
            # Calculate the position of the dot
            dot_position = self.player.rect.center + direction * i * dot_spacing
            # Draw the dot
            pygame.draw.circle(self.window, (255, 255, 255), (int(dot_position.x), int(dot_position.y)), 5)

        # Move the dots towards the flag
        for dot in self.dots:
            dot['position'] += direction * dot['speed']
            # If the dot has reached the flag, respawn it at the start point
            if (dot['position'] - Vector2(self.nearestFlag.rect.center)).length() < dot['speed']:
                dot['position'] = Vector2(self.player.rect.center)
            # Draw the dot
            pygame.draw.circle(self.window, (255, 255, 255), (int(dot['position'].x), int(dot['position'].y)), 5)

        if pygame.time.get_ticks() - self.lastDot >= DOT_DURATION:

            Dot(self, self.player.rect.center , self.nearestFlag.rect.center)
            self.lastDot = pygame.time.get_ticks()
        print(self.player.rect.center)

        for i in range(int(nearestFlagDistance) // 3000):

            dot = Dot(self, self.player.rect.center, self.nearestFlag.rect.center)
            dot.rect.center += dot.velocity * i
            """

        if self.debugMode:

            self.map.DrawGrid(self.window)

            for sprite in self.allSprites:

                pygame.draw.rect(self.window, (255, 0, 0), self.camera.Apply(sprite.rect), 1)

            for sprite in self.walls:

                pygame.draw.rect(self.window, (255, 0, 0), self.camera.Apply(sprite.rect), 1)

            pygame.draw.rect(self.window, (255, 0, 0), self.camera.Apply(self.player.hitRect), 1)

        self.window.blit(self.cursor, self.mousePosition)

    def Exit(self):

        self.isRunning = False
        pygame.quit()
        exit()