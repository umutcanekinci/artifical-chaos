from scripts.animation_clip import AnimationClip
from pygame import SRCALPHA, Surface
from pygame.sprite import Sprite

class Animator(Sprite):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image = Surface((0, 0), SRCALPHA)
        self.animations = {}
        self.current_animation = None
        self.current_frame = 0
        self.frame_time = 0
    
    def add_animation(self, animation_clip):
        if not isinstance(animation_clip, AnimationClip):
            raise TypeError("Expected an instance of AnimationClip")
        
        self.animations[animation_clip.name] = animation_clip

    def set_animation(self, name):
        if self.current_animation == self.animations.get(name):
            return
        
        if name in self.animations:
            self.current_animation = self.animations.get(name)
            self.current_frame = 0
            self.frame_time = 0
            self.image = self.current_animation[self.current_frame]
        else:
            raise ValueError(f"Animation '{name}' not found")
         
    def update(self, delta_time):
        if self.current_animation is None:
            return
    
        self.frame_time += delta_time
        if self.frame_time >= self.current_animation.duration / len(self.current_animation):
            self.frame_time = 0
            self.current_frame = (self.current_frame + 1) % len(self.current_animation)

            self.image = self.current_animation[self.current_frame]
            self.rect = self.image.get_rect(center=self.rect.center)