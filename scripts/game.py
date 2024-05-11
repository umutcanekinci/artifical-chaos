import pygame
from scripts.map import Map, Camera
from scripts.player import Player
from scripts.settings import *
from sys import exit

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
        self.allSprites = pygame.sprite.Group()
        self.walls = pygame.sprite.Group()
        self.map = Map(self)
        self.camera = Camera(self.rect.size, self.map)
        self.player = Player(self, self.map.rect.center)

    def Start(self):

        self.isRunning = True

        while self.isRunning:

            self.clock.tick(FPS)
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

    def Update(self):
        
        self.camera.Follow(self.player.rect)
        self.allSprites.update()

    def Draw(self):

        self.window.fill((0, 0, 0))
        self.camera.Draw(self.window, self.map)
        self.camera.Draw(self.window, self.allSprites)

    def Exit(self):

        self.isRunning = False
        pygame.quit()
        exit()