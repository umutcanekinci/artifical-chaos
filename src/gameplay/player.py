import random

import pygame
from pygame.math import Vector2
from typing import override

from pygamine import GameObject
from pygamine import SpriteRenderer2D
from pygamine import Animator
from pygamine import SpriteSheet
from pygamine import scale_by
from pygamine import ImagePath

from util.constants import *
from gameplay.collision import collide, nearby_walls
from gameplay.animation import add_directional_clips
from gameplay.combat import apply_damage, find_nearest, has_line_of_sight, muzzle_position, raycast, ready_to_attack
from gameplay.effects import BulletImpact, FloatingText, HitSpark, MuzzleFlash, Tracer
from gameplay.ui import draw_health_bar


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
        self.max_hp = 100
        self.hp = self.max_hp
        self.ms = 100
        self.fire_damage = PLAYER_FIRE_DAMAGE
        self.fire_cooldown_ms = PLAYER_FIRE_COOLDOWN_MS
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
        self.squad_stance = "engage"

        self.add_component(SpriteRenderer2D)
        self.add_component(Animator)
        add_directional_clips(self, ImagePath("SquadLeader", "soliders"),
                              {"idle": 0, "walking": 1, "fire": 3, "death": 5})
        self.get_component(Animator).play("idle_0")

        self.rank_position = Vector2(0, RANK_SIZE * SCALE_FACTOR)
        self.rank_rect = pygame.Rect(0, 0, RANK_SIZE * SCALE_FACTOR, RANK_SIZE * SCALE_FACTOR)
        self.rank_sheet = SpriteSheet.from_path(ImagePath("squad-insignia", "ui"))
        self.rank_image = self.get_rank_image()

        self._squad_stance_font = pygame.font.SysFont("Arial", SQUAD_STANCE_HUD_FONT_SIZE, bold=True)

        game.all_sprites.append(self)

    def get_rank_image(self) -> pygame.Surface:
        # squad-insignia.png is 240x216 (10x9 @RANK_SIZE); only columns 5-9
        # are the actual insignia column-block (5 wide), so this must wrap
        # with `% 5`, not `% 6` -- `% 6` used to reach col 10 (5 + 5), one
        # past the sheet's last valid column (9), raising a subsurface
        # ValueError. rank is also clamped to MAX_RANK here (not on
        # self.rank itself, which keeps counting for rank-up purposes) as a
        # second guard against the row math (rank // 5) ever overflowing
        # the sheet's 9 rows too.
        rank = min(self.rank, MAX_RANK)
        frame = self.rank_sheet.frame(5 + rank % 5, rank // 5, RANK_SIZE, RANK_SIZE)
        return scale_by(frame, SCALE_FACTOR)

    def rank_up(self):
        self.rank += 1
        self.rank_image = self.get_rank_image()

        stat_count = (RANK_UP_STATS_MANY_RANKS if len(self.game.flags) >= RANK_UP_MANY_RANKS_THRESHOLD
                     else RANK_UP_STATS_FEW_RANKS)
        stats = random.sample(list(RANK_UP_STAT_LABELS), min(stat_count, len(RANK_UP_STAT_LABELS)))

        for i, stat in enumerate(stats):
            self._apply_rank_bonus(stat)
            offset_index = 2 * i - (len(stats) - 1)  # spreads picks out; centered for a single pick
            FloatingText(self.game, self.rect.midtop, RANK_UP_STAT_LABELS[stat],
                        RANK_UP_STAT_COLORS[stat], offset_index=offset_index)

    def _apply_rank_bonus(self, stat: str) -> None:
        if stat == "hp":
            self.max_hp += RANK_UP_HP_BONUS
            self.hp += RANK_UP_HP_BONUS
        elif stat == "speed":
            self.ms += RANK_UP_SPEED_BONUS
        elif stat == "fire_rate":
            self.fire_cooldown_ms = max(RANK_UP_FIRE_RATE_MIN_MS, self.fire_cooldown_ms - RANK_UP_FIRE_RATE_BONUS_MS)
        elif stat == "damage":
            self.fire_damage += RANK_UP_DAMAGE_BONUS

    def get_soldier(self):
        for soldier in self.game.soldiers:
            if (Vector2(soldier.rect.center) - Vector2(self.rect.center)).length() < 50:
                soldier.add_to_army()

    def toggle_squad_stance(self) -> None:
        """Flips between "engage" (default -- every in-army soldier ranges
        out independently to fight whatever's nearest, see Soldier.engage())
        and "guard" (soldiers hold a tight escort formation and ignore
        threats far from the commander). Bound to Tab in Game.handle_event().
        Purely a stance switch, not a targeting command -- soldiers still
        pick their own nearest target on their own, see SQUAD_GUARD_*
        constants in util/constants.py."""
        self.squad_stance = "guard" if self.squad_stance == "engage" else "engage"
        FloatingText(self.game, self.rect.midtop, SQUAD_STANCE_LABELS[self.squad_stance],
                    SQUAD_STANCE_COLORS[self.squad_stance])

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
        walls = nearby_walls(self.game, self.hit_rect)

        self.velocity = self.acceleration * self.game.delta_time * self.ms
        self.velocity -= self.velocity * FRICTION

        self.position.x += self.velocity.x * self.game.delta_time
        self.hit_rect.centerx = self.position.x
        if collide(self, 'x', walls):
            self.position.x = self.hit_rect.centerx

        self.position.y += self.velocity.y * self.game.delta_time
        self.hit_rect.centery = self.position.y
        if collide(self, 'y', walls):
            self.position.y = self.hit_rect.centery

        self.hit_rect.center = self.rect.center = self.position

    def aim_at_mouse(self) -> None:
        mouse_world = self.game.camera.screen_to_world(self.game.mouse.position)
        self.facing = 1 if mouse_world.x < self.position.x else 0

    def attack(self, target, damage: int, cooldown_ms: int) -> None:
        now = pygame.time.get_ticks()
        if not ready_to_attack(now, self.last_attack_time, cooldown_ms):
            return
        self.last_attack_time = now
        muzzle = muzzle_position(self.position, self.facing, MUZZLE_OFFSET_X, MUZZLE_OFFSET_Y)
        MuzzleFlash(self.game, muzzle, self.facing)
        Tracer(self.game, muzzle, target.position)
        HitSpark(self.game, target.position)
        if apply_damage(target, damage):
            target.die()

    def fire_at_nothing(self) -> None:
        """Cosmetic counterpart to attack() for when the mouse is held but
        no drone is in range -- still gated by the same fire_cooldown_ms
        (so holding the button against a wall doesn't spam decals every
        frame), but there's no target and nothing to damage. Fires a
        raycast (gameplay/combat.py's raycast(), cosmetic-only -- never
        gates real hit resolution) toward the mouse cursor; a MuzzleFlash
        and Tracer always play either way (the gun still visibly fires),
        and a BulletImpact decal drops at the wall if the ray hit one."""
        now = pygame.time.get_ticks()
        if not ready_to_attack(now, self.last_attack_time, self.fire_cooldown_ms):
            return
        self.last_attack_time = now

        mouse_world = self.game.camera.screen_to_world(self.game.mouse.position)
        direction = Vector2(mouse_world) - self.position
        if direction.length() == 0:
            return
        hit_point = raycast(self.position, direction, PLAYER_FIRE_RANGE, self.game.walls)
        end_point = hit_point if hit_point is not None else self.position + direction.normalize() * PLAYER_FIRE_RANGE

        muzzle = muzzle_position(self.position, self.facing, MUZZLE_OFFSET_X, MUZZLE_OFFSET_Y)
        MuzzleFlash(self.game, muzzle, self.facing)
        Tracer(self.game, muzzle, end_point)
        if hit_point is not None:
            BulletImpact(self.game, hit_point)

    def shoot(self) -> bool:
        """Fires at the nearest drone in range while the mouse button is
        held. Movement isn't interrupted by firing -- only this frame's
        animation status is (can't blend "walk" and "fire" without a
        dedicated combined clip, which the asset pack doesn't have).

        A found target behind a wall (no combat.has_line_of_sight()) falls
        back to fire_at_nothing() exactly like having no target at all --
        the shot still fires cosmetically toward the mouse cursor (not
        toward the blocked target), and drops a BulletImpact if *that*
        aim direction hits a wall too. No "walk toward it" concern here
        the way Soldier/Drone have: the player is directly controlled, so
        there's no autonomous-approach behavior that could get stuck."""
        if not pygame.mouse.get_pressed()[0]:
            return False
        self.aim_at_mouse()
        self.status = "fire"
        target = find_nearest(self.position, self.game.robots, PLAYER_FIRE_RANGE)
        if target is not None and has_line_of_sight(self.position, target.position, self.game.walls):
            self.attack(target, self.fire_damage, self.fire_cooldown_ms)
        else:
            self.fire_at_nothing()
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

    def health_fraction(self) -> float:
        return max(0.0, self.hp) / self.max_hp

    def draw_health(self, surface, camera) -> None:
        draw_health_bar(surface, camera, self.rect, self.hp, self.max_hp, always=True)

    def draw_squad_stance(self, surface) -> None:
        """A persistent, always-visible HUD label for squad_stance -- fixed
        to a screen corner (not world-space like draw_rank()/draw_health(),
        so it stays put regardless of where the player wanders) since the
        one-shot FloatingText toggle_squad_stance() already pops is easy to
        miss if you looked away for a second. Same label/color mapping as
        that popup (SQUAD_STANCE_LABELS/COLORS), just persistent instead of
        fading out."""
        label = self._squad_stance_font.render(SQUAD_STANCE_LABELS[self.squad_stance], True,
                                               SQUAD_STANCE_COLORS[self.squad_stance])
        rect = label.get_rect(bottomleft=(SQUAD_STANCE_HUD_MARGIN, surface.get_height() - SQUAD_STANCE_HUD_MARGIN))
        surface.blit(label, rect)
