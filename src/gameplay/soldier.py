import random

import pygame
from pygame.math import Vector2
from typing import override

from pygame_core.ecs.game_object import GameObject
from pygame_core.ecs.components.sprite_renderer2d import SpriteRenderer2D
from pygame_core.ecs.components.animator import Animator
from pygame_core.asset_path import ImagePath
from pygame_core.sprite_sheet import SpriteSheet
from pygame_core.image import scale

from util.constants import *
from gameplay.collision import collide
from gameplay.animation import add_directional_clips
from gameplay.combat import (
    apply_damage, find_all_in_range, find_nearest, has_line_of_sight, muzzle_position, ready_to_attack,
)
from gameplay.effects import BigExplosion, FloatingText, Grenade, HitSpark, MuzzleFlash, Smoke, Tracer
from gameplay.ui import draw_health_bar


class Soldier(GameObject):
    """A recruitable ally. `soldier_class` looks up movement speed and
    fire stats from SOLDIER_CLASSES (util/constants.py) and picks the
    matching sprite sheet -- five of six classes are wired up this way
    (Assault/Sniper/MachineGunner/AntiTank single-target, Grenadier splash
    via `splash_radius`, see attack()); RadioOperator still needs a support-
    ability mechanic this codebase doesn't have yet, see GDD.md."""

    def __init__(self, game, position, soldier_class: str = "Assault-Class"):
        super().__init__(name="soldier")
        self.game = game
        self.max_hp = 100
        self.hp = self.max_hp
        stats = SOLDIER_CLASSES[soldier_class]
        self.ms = stats["speed"]
        self.fire_range = stats["fire_range"]
        self.fire_damage = stats["fire_damage"]
        self.fire_cooldown_ms = stats["fire_cooldown_ms"]
        self.splash_radius = stats["splash_radius"]
        self.support_cooldown_ms = stats["support_cooldown_ms"]

        self.acceleration = Vector2()
        self.velocity = Vector2()
        self.position = Vector2(position)
        self.rotation = Vector2()

        self.rect.size = (SPRITE_SIZE * SCALE_FACTOR, SPRITE_SIZE * SCALE_FACTOR)
        self.hit_rect = pygame.Rect(0, 0, SPRITE_SIZE * SCALE_FACTOR / 2, SPRITE_SIZE * SCALE_FACTOR / 2)
        self.rect.center = self.hit_rect.center = position

        self.status = "idle"
        self.facing = 0
        self.is_in_army = False
        self.last_attack_time = 0
        self.last_support_time = 0

        self.add_component(SpriteRenderer2D)
        self.add_component(Animator)
        add_directional_clips(self, ImagePath(soldier_class, "soliders"),
                              {"idle": 0, "walking": 1, "fire": 3})
        self.get_component(Animator).play("idle_0")

        marker_sheet = SpriteSheet.from_path(ImagePath("selection-circles", "ui"))
        marker_frame = marker_sheet.frame(RECRUITED_MARKER_COL, RECRUITED_MARKER_ROW,
                                          RECRUITED_MARKER_SOURCE_SIZE, RECRUITED_MARKER_SOURCE_SIZE)
        self.recruited_marker_image = scale(marker_frame,
                                            (RECRUITED_MARKER_FINAL_SIZE, RECRUITED_MARKER_FINAL_SIZE))

        game.all_sprites.append(self)
        game.soldiers.append(self)

    def add_to_army(self):
        self.is_in_army = True

    def walk(self, hold_distance: float = SOLDIER_HOLD_DISTANCE):
        if self.game.keys[pygame.K_a] or self.game.keys[pygame.K_LEFT]:
            self.facing = 1
        if self.game.keys[pygame.K_d] or self.game.keys[pygame.K_RIGHT]:
            self.facing = 0

        self.rotation = self.game.player.position - self.position

        if self.rotation.length() > hold_distance:
            self.status = "walking"
            self.acceleration = self.rotation.normalize() * self.ms
        else:
            self.acceleration = Vector2()
            self.status = "idle"

    def move(self):
        self.velocity = self.acceleration * self.game.delta_time * self.ms
        self.velocity -= self.velocity * FRICTION * self.game.delta_time

        self.position.x += self.velocity.x * self.game.delta_time
        self.hit_rect.centerx = self.position.x
        if collide(self, 'x', self.game.walls):
            self.position.x = self.hit_rect.centerx

        self.position.y += self.velocity.y * self.game.delta_time
        self.hit_rect.centery = self.position.y
        if collide(self, 'y', self.game.walls):
            self.position.y = self.hit_rect.centery

        self.hit_rect.center = self.rect.center = self.position

    def avoid_entities(self):
        for soldier in self.game.soldiers:
            if soldier is self:
                continue
            dist = self.position - soldier.position
            distance = dist.length()
            if distance == 0:
                # Exactly overlapping: normalize() would raise on a zero
                # vector, and with no direction to push apart they'd stay
                # stuck together forever otherwise. Break the tie
                # deterministically so the two soldiers push opposite
                # ways instead of both doing nothing.
                direction = Vector2(1, 0) if id(self) < id(soldier) else Vector2(-1, 0)
                self.acceleration += direction * self.ms
            elif distance < AVOID_RADIUS:
                # Push harder the closer they are -- a constant unit-length
                # nudge (the old behavior) shoves a soldier already
                # touching another no harder than one barely inside the
                # radius, which isn't enough to stop them drifting into a
                # visible overlap once close.
                strength = (AVOID_RADIUS - distance) / AVOID_RADIUS
                self.acceleration += dist.normalize() * strength * self.ms

    def attack(self, target, damage: int, cooldown_ms: int) -> None:
        now = pygame.time.get_ticks()
        if not ready_to_attack(now, self.last_attack_time, cooldown_ms):
            return
        self.last_attack_time = now

        if self.splash_radius > 0:
            # Grenadier-Class: splash lands on everyone within splash_radius
            # of the *thrown-at* point, not just target -- a cluster of
            # drones near it all take damage, not only the nearest one.
            # Still hitscan in spirit (see gameplay/combat.py): the damage
            # resolves instantly at throw time, the Grenade/BigExplosion are
            # purely cosmetic on top.
            throw_point = muzzle_position(self.position, self.facing, MUZZLE_OFFSET_X, MUZZLE_OFFSET_Y)
            Grenade(self.game, throw_point, target.position)
            for hit in find_all_in_range(target.position, self.game.robots, self.splash_radius):
                HitSpark(self.game, hit.position)
                if apply_damage(hit, damage):
                    hit.die()
            BigExplosion(self.game, target.position)
            Smoke(self.game, target.position)
            return

        muzzle = muzzle_position(self.position, self.facing, MUZZLE_OFFSET_X, MUZZLE_OFFSET_Y)
        MuzzleFlash(self.game, muzzle, self.facing)
        Tracer(self.game, muzzle, target.position)
        HitSpark(self.game, target.position)
        if apply_damage(target, damage):
            target.die()

    def engage(self) -> None:
        """Fights the nearest drone in range instead of following the
        player, if one's close enough; otherwise falls back to walk().
        RadioOperator-Class doesn't fight at all -- support_cooldown_ms > 0
        means it calls in a reinforcement soldier on a cooldown instead
        (see call_reinforcement()), then always falls back to walk() since
        it never occupies itself with combat.

        Still finds and holds on a target the same as always while the
        player is moving -- status/facing/acceleration all update, so it
        visibly aims -- but attack() itself only actually fires while the
        player is under SQUAD_ATTACK_MAX_PLAYER_SPEED (see util/
        constants.py): keeping the player moving leaves an in-range soldier
        stuck aiming at nothing instead of following, so "stop to let your
        squad finish this fight" vs. "keep moving and leave them behind,
        mid-aim" becomes a real decision rather than something that just
        happens automatically in the background.

        Player.squad_stance (toggled with Tab, see Game.handle_event()) adds
        one more filter on top when set to "guard": walk()'s hold distance
        tightens to SQUAD_GUARD_HOLD_DISTANCE (escort formation instead of
        ranging out ~100px), and a found target gets discarded if it's more
        than SQUAD_GUARD_ENGAGE_RADIUS away from the player -- a soldier with
        a long fire_range (Sniper-Class) won't wander off toward a distant
        fight while the squad's supposed to be holding close. Neither of
        these touches *which* target gets picked, only where the soldier's
        willing to look for one, so the no-individual-micromanagement pillar
        holds the same as the stationary-fire gate above.

        A target behind a wall (no `combat.has_line_of_sight()`) is treated
        as if none were found at all -- see the comment at that check for
        why this soldier falls back to following the player instead of
        holding its aim on a blocked target the way Drone.engage() holds
        and keeps approaching."""
        guarding = self.game.player.squad_stance == "guard"
        hold_distance = SQUAD_GUARD_HOLD_DISTANCE if guarding else SOLDIER_HOLD_DISTANCE

        if self.support_cooldown_ms > 0:
            if self.call_reinforcement():
                self.acceleration = Vector2()
                self.status = "fire"  # reuses the generic "doing something" pose, like Grenadier's throw
            else:
                self.walk(hold_distance)
            return

        target = find_nearest(self.position, self.game.robots, self.fire_range)
        if target is not None:
            if guarding and (target.position - self.game.player.position).length() > SQUAD_GUARD_ENGAGE_RADIUS:
                target = None  # too far from the commander to bother with while guarding
            elif not has_line_of_sight(self.position, target.position, self.game.walls):
                # Blocked by a wall -- soldiers never approach a target on
                # their own (unlike Drone.engage(), which walks closer when
                # blocked), so holding onto a blocked target would freeze
                # this soldier in place indefinitely. Falling back to
                # walk() instead means it keeps following the player, which
                # naturally changes the geometry over time instead of
                # standing stuck aiming at a wall forever.
                target = None

        if target is None:
            self.walk(hold_distance)
            return

        self.acceleration = Vector2()
        self.status = "fire"
        delta = target.position - self.position
        if abs(delta.x) > FACING_DEADZONE:
            self.facing = 1 if delta.x < 0 else 0
        if self.game.player.velocity.length() < SQUAD_ATTACK_MAX_PLAYER_SPEED:
            self.attack(target, self.fire_damage, self.fire_cooldown_ms)

    def call_reinforcement(self) -> bool:
        """RadioOperator-Class's support ability: on a cooldown
        (support_cooldown_ms), spawns a fresh combat-capable Soldier near
        itself, already added to the army -- same one-line join every
        proximity-recruited soldier gets (Player.get_soldier()), just
        triggered by a radio call instead of the player walking up to a
        dormant one. Returns whether a reinforcement was actually called
        this frame, so engage() knows whether to hold still and play its
        "calling it in" pose or fall back to walking."""
        now = pygame.time.get_ticks()
        if not ready_to_attack(now, self.last_support_time, self.support_cooldown_ms):
            return False
        self.last_support_time = now

        combat_classes = [name for name, stats in SOLDIER_CLASSES.items()
                          if stats["support_cooldown_ms"] == 0]
        soldier_class = random.choice(combat_classes)
        offset = Vector2(random.uniform(-1, 1), random.uniform(-1, 1))
        if offset.length() > 0:
            offset.scale_to_length(RADIO_OPERATOR_REINFORCEMENT_OFFSET)
        reinforcement = Soldier(self.game, self.position + offset, soldier_class=soldier_class)
        reinforcement.add_to_army()

        FloatingText(self.game, self.rect.midtop, RADIO_OPERATOR_CALL_LABEL, RADIO_OPERATOR_CALL_COLOR)
        return True

    @override
    def update(self):
        if self.is_in_army:
            self.engage()
            self.avoid_entities()
            self.move()

        self.get_component(Animator).play(f"{self.status}_{self.facing}")
        super().update()

    def die(self):
        self.active = False

    def draw_health(self, surface, camera) -> None:
        draw_health_bar(surface, camera, self.rect, self.hp, self.max_hp)

    def draw_recruited_marker(self, surface, camera) -> None:
        if not self.is_in_army:
            return
        image = camera.scale_image(self.recruited_marker_image)
        world_pos = (self.rect.centerx, self.rect.centery + RECRUITED_MARKER_Y_OFFSET)
        center = camera.world_to_screen(world_pos)
        rect = image.get_rect(center=(center.x, center.y))
        surface.blit(image, rect)
