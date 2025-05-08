import pygame

class Transform:
    def __init__(self, position=(0, 0), rotation=0, scale=(1, 1)):
        # self.position = position
        # self.rotation = rotation
        # self.scale = scale
        self.rect = pygame.Rect(0, 0, scale[0], scale[1])
        self.hitRect = pygame.Rect(0, 0, scale[0] / 2, scale[1] / 2)
        self.rect.center = self.hitRect.center = position

    def __repr__(self):
        pass
        #return f"Transform(position={self.position}, rotation={self.rotation}, scale={self.scale})"