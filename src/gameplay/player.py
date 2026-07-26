import pygame
from pygame.math import Vector2
from typing import override

from pygame_core.ecs.game_object import GameObject
from pygame_core.ecs.components.sprite_renderer2d import SpriteRenderer2D
from pygame_core.ecs.components.animator import Animator
from pygame_core.sprite_sheet import SpriteSheet
from pygame_core.image import scale_by
from pygame_core.asset_path import ImagePath

from util.constants import *
from gameplay.collision import collide
from gameplay.animation import add_directional_clips
from gameplay.combat import apply_damage, find_nearest, ready_to_attack
from gameplay.effects import HitSpark, MuzzleFlash, Tracer


class Footprint(GameObject):

    def __init__(self, game, position):
        super().__init__(name="footprint")
        self.game = game

        self.rect.size = (SPRITE_SIZE, SPRITE_SIZE)
        self.rect.center = position
        self.renderer = self.add_component(SpriteRenderer2D)

        self.size = 1
        self._render()
        self.creation_time = pygame.time.get_ticks()
        game.all_sprites.append(self)

    def _render(self):
        image = pygame.Surface((SPRITE_SIZE, SPRITE_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(image, (255, 255, 255), (SPRITE_SIZE // 2, SPRITE_SIZE // 2), max(1, self.size // 3), 1)
        self.renderer.set_image(image)

    @override
    def update(self):
        if pygame.time.get_ticks() - self.creation_time >= FOOTPRINT_DURATION * 2:
            self.active = False
            return

        self.size += 1
        self._render()


class Player(GameObject):

    def __init__(self, game, position):
        super().__init__(name="player")
        self.game = game
        self.hp = 100
        self.ms = 100
        self.rank = 0
        self.acceleration = Vector2()
        self.velocity = Vector2()
        self.position = Vector2(position)
        self.rotation = Vector2()

        self.rect.size = (SPRITE_SIZE * SCALE_FACTOR, SPRITE_SIZE * SCALE_FACTOR)
        self.hit_rect = pygame.Rect(0, 0, SPRITE_SIZE * SCALE_FACTOR / 2, SPRITE_SIZE * SCALE_FACTOR / 2)
        self.rect.center = self.hit_rect.center = position

        self.status = "idle"
        self.facing = 0
        self.left_foot = True
        self.last_footprint = 0
        self.last_attack_time = 0
        self.is_dead = False

        self.add_component(SpriteRenderer2D)
        self.add_component(Animator)
        add_directional_clips(self, ImagePath("SquadLeader", "soliders"),
                              {"idle": 0, "walking": 1, "fire": 3, "death": 5})
        self.get_component(Animator).play("idle_0")

        self.rank_position = Vector2(0, RANK_SIZE * SCALE_FACTOR)
        self.rank_rect = pygame.Rect(0, 0, RANK_SIZE * SCALE_FACTOR, RANK_SIZE * SCALE_FACTOR)
        self.rank_sheet = SpriteSheet.from_path(ImagePath("squad-insignia", "UI"))
        self.rank_image = self.get_rank_image()

        game.all_sprites.append(self)

    def get_rank_image(self) -> pygame.Surface:
        frame = self.rank_sheet.frame(5 + self.rank % 6, self.rank // 5, RANK_SIZE, RANK_SIZE)
        return scale_by(frame, SCALE_FACTOR)

    def rank_up(self):
        self.rank += 1
        self.rank_image = self.get_rank_image()

    def get_soldier(self):
        for soldier in self.game.soldiers:
            if (Vector2(soldier.rect.center) - Vector2(self.rect.center)).length() < 50:
                soldier.add_to_army()

    def walk(self):
        if self.game.keys[pygame.K_w] or self.game.keys[pygame.K_UP]:
            self.rotation.y = -1
        elif self.game.keys[pygame.K_s] or self.game.keys[pygame.K_DOWN]:
            self.rotation.y = 1
        else:
            self.rotation.y = 0

        if self.game.keys[pygame.K_a] or self.game.keys[pygame.K_LEFT]:
            self.rotation.x = -1
            self.facing = 1
        elif self.game.keys[pygame.K_d] or self.game.keys[pygame.K_RIGHT]:
            self.rotation.x = 1
            self.facing = 0
        else:
            self.rotation.x = 0

        if self.rotation.length() > 0:
            self.status = "walking"
            self.acceleration = self.rotation.normalize() * self.ms

            if pygame.time.get_ticks() - self.last_footprint >= FOOTPRINT_DURATION:
                if self.left_foot:
                    Footprint(self.game, Vector2(self.rect.center) + Vector2(20, 30))
                    self.left_foot = False
                else:
                    Footprint(self.game, Vector2(self.rect.center) + Vector2(15, 30))
                    self.left_foot = True
                self.last_footprint = pygame.time.get_ticks()
        else:
            self.acceleration = Vector2()
            self.status = "idle"

    def move(self):
        self.velocity = self.acceleration * self.game.delta_time * self.ms
        self.velocity -= self.velocity * FRICTION
        self.position += self.velocity * self.game.delta_time

        self.rect.center = self.hit_rect.center = self.position

        self.hit_rect.centerx += self.velocity.x
        collide(self, 'x', self.game.walls)
        self.hit_rect.centery += self.velocity.y
        collide(self, 'y', self.game.walls)

    def aim_at_mouse(self) -> None:
        mouse_world = self.game.camera.screen_to_world(self.game.mouse.position)
        self.facing = 1 if mouse_world.x < self.position.x else 0

    def attack(self, target, damage: int, cooldown_ms: int) -> None:
        now = pygame.time.get_ticks()
        if not ready_to_attack(now, self.last_attack_time, cooldown_ms):
            return
        self.last_attack_time = now
        MuzzleFlash(self.game, self.position, self.facing)
        Tracer(self.game, self.position, target.position)
        HitSpark(self.game, target.position)
        if apply_damage(target, damage):
            target.die()

    def shoot(self) -> bool:
        """Fires at the nearest drone in range while the mouse button is
        held. Movement isn't interrupted by firing -- only this frame's
        animation status is (can't blend "walk" and "fire" without a
        dedicated combined clip, which the asset pack doesn't have)."""
        if not pygame.mouse.get_pressed()[0]:
            return False
        self.aim_at_mouse()
        self.status = "fire"
        target = find_nearest(self.position, self.game.robots, PLAYER_FIRE_RANGE)
        if target is not None:
            self.attack(target, PLAYER_FIRE_DAMAGE, PLAYER_FIRE_COOLDOWN_MS)
        return True

    @override
    def update(self):
        if self.is_dead:
            return

        self.get_soldier()
        self.walk()
        self.move()
        self.shoot()
        self.get_component(Animator).play(f"{self.status}_{self.facing}")
        super().update()

    def die(self):
        if self.is_dead:
            return
        self.is_dead = True
        self.acceleration = Vector2()
        self.velocity = Vector2()
        self.status = "death"
        self.get_component(Animator).play(f"death_{self.facing}")

    def draw_rank(self, surface, camera) -> None:
        self.rank_rect.center = self.position - self.rank_position
        topleft = camera.world_to_screen(self.rank_rect.topleft)
        surface.blit(camera.scale_image(self.rank_image), (topleft.x, topleft.y))
