import pygame
from pygame.math import Vector2
from typing import override

from pygamine.ecs.game_object import GameObject
from pygamine.ecs.components.sprite_renderer2d import SpriteRenderer2D
from pygamine.ecs.components.animator import Animator
from pygamine.asset_path import ImagePath

from util.constants import *
from gameplay.collision import collide
from gameplay.animation import add_directional_clips, add_oneshot_clip
from gameplay.combat import apply_damage, find_nearest, has_line_of_sight, muzzle_position, ready_to_attack
from gameplay.effects import Explosion, HitSpatter, LaserFlash, MuzzleFlash, Smoke, Tracer
from gameplay.ui import draw_health_bar


class Drone(GameObject):
    """A basic drone: idle until something enters AGGRO_RADIUS, then chases
    the nearest player/in-army-soldier, melees at point-blank range or fires
    at mid-range, and holds a destroyed frame for DESTROYED_DURATION_MS
    before being purged (see Game._purge_inactive).

    `drone_type` looks up stats + sheet layout from DRONE_TYPES
    (util/constants.py). Subclasses below just pin the type so
    `Scarab(game, pos)` reads the same as before."""

    def __init__(self, game, position, drone_type: str) -> None:
        super().__init__(name=drone_type.lower())
        self.game = game
        stats = DRONE_TYPES[drone_type]
        self.max_hp = stats["hp"]
        self.hp = self.max_hp
        self.ms = stats["speed"]
        self.melee_range = stats["melee_range"]
        self.fire_range = stats["fire_range"]
        self.melee_damage = stats["melee_damage"]
        self.fire_damage = stats["fire_damage"]
        self.melee_cooldown_ms = stats["melee_cooldown_ms"]
        self.fire_cooldown_ms = stats["fire_cooldown_ms"]
        self.has_destroyed_clip = stats["destroyed_row"] is not None
        self.muzzle_effect = stats["muzzle_effect"]
        self.stand_off_range = stats["stand_off_range"]

        self.acceleration = Vector2()
        self.velocity = Vector2()
        self.position = Vector2(position)

        sprite_size = stats["sprite_size"]
        self.rect.size = (sprite_size * SCALE_FACTOR, sprite_size * SCALE_FACTOR)
        self.hit_rect = pygame.Rect(0, 0, sprite_size * SCALE_FACTOR / 2, sprite_size * SCALE_FACTOR / 2)
        self.rect.center = self.hit_rect.center = position

        self.status = "idle"
        self.facing = 0
        self.last_attack_time = 0
        self.death_time = 0

        self.add_component(SpriteRenderer2D)
        self.add_component(Animator)
        add_directional_clips(self, ImagePath(drone_type, "robots"),
                              stats["clip_rows"], size=sprite_size)
        if self.has_destroyed_clip:
            add_oneshot_clip(self, ImagePath(drone_type, "robots"),
                             row=stats["destroyed_row"], size=sprite_size)
        self.get_component(Animator).play("idle_0")

        game.all_sprites.append(self)
        game.robots.append(self)

    def get_target(self):
        candidates = [self.game.player] + [s for s in self.game.soldiers if s.is_in_army]
        return find_nearest(self.position, candidates, AGGRO_RADIUS)

    def engage(self) -> None:
        target = self.get_target()
        if target is None:
            self.acceleration = Vector2()
            self.status = "idle"
            return

        delta = Vector2(target.position) - self.position
        distance = delta.length()

        if distance <= self.melee_range:
            self.acceleration = Vector2()
            self.status = "melee"
            self.attack(target, self.melee_damage, self.melee_cooldown_ms)
        elif distance <= self.fire_range and has_line_of_sight(self.position, target.position, self.game.walls):
            self.status = "fire"
            if self.stand_off_range > 0 and distance < self.stand_off_range:
                # Kite: back away while still firing instead of holding
                # ground, so a target that closes in doesn't just let a
                # ranged-only drone stand there and trade hits at melee
                # range with nothing to hit back with.
                self.acceleration = -delta.normalize() * self.ms
            else:
                self.acceleration = Vector2()
            self.attack(target, self.fire_damage, self.fire_cooldown_ms)
        else:
            # Either out of fire_range, or in range but a wall blocks the
            # shot (has_line_of_sight) -- both cases close the distance the
            # same way. A blocked drone never stands still firing at a
            # wall; it keeps approaching, which either reaches melee range
            # (unconditional, no LOS check needed once actually adjacent)
            # or the target moves and the sightline opens back up.
            self.status = "walking"
            self.acceleration = delta.normalize() * self.ms

        if abs(delta.x) > FACING_DEADZONE:
            self.facing = 1 if delta.x < 0 else 0

    def attack(self, target, damage: int, cooldown_ms: int) -> None:
        now = pygame.time.get_ticks()
        if not ready_to_attack(now, self.last_attack_time, cooldown_ms):
            return
        self.last_attack_time = now
        if self.status == "fire":  # melee has no muzzle/tracer -- no gun to flash
            muzzle = muzzle_position(self.position, self.facing, MUZZLE_OFFSET_X, MUZZLE_OFFSET_Y)
            if self.muzzle_effect == "laser":
                LaserFlash(self.game, muzzle, self.facing)
            else:
                MuzzleFlash(self.game, muzzle, self.facing)
            Tracer(self.game, muzzle, target.position)
        HitSpatter(self.game, target.position)
        if apply_damage(target, damage):
            target.die()

    def move(self) -> None:
        self.velocity = self.acceleration * self.game.delta_time * self.ms
        self.velocity -= self.velocity * FRICTION

        self.position.x += self.velocity.x * self.game.delta_time
        self.hit_rect.centerx = self.position.x
        if collide(self, 'x', self.game.walls):
            self.position.x = self.hit_rect.centerx

        self.position.y += self.velocity.y * self.game.delta_time
        self.hit_rect.centery = self.position.y
        if collide(self, 'y', self.game.walls):
            self.position.y = self.hit_rect.centery

        self.hit_rect.center = self.rect.center = self.position

    def die(self) -> None:
        if self.status == "destroyed" or not self.active:
            return
        self.acceleration = Vector2()
        self.velocity = Vector2()
        Explosion(self.game, self.position)
        Smoke(self.game, self.position)
        if self.has_destroyed_clip:
            self.status = "destroyed"
            self.death_time = pygame.time.get_ticks()
        else:
            self.active = False  # no destroyed pose to hold -- remove immediately

    @override
    def update(self) -> None:
        if not self.active:
            return

        if self.status == "destroyed":
            if pygame.time.get_ticks() - self.death_time >= DESTROYED_DURATION_MS:
                self.active = False
        else:
            self.engage()
            self.move()

        self.get_component(Animator).play(f"{self.status}_{self.facing}")
        super().update()

    def draw_health(self, surface, camera) -> None:
        if self.status == "destroyed":  # no bar over a wreck
            return
        draw_health_bar(surface, camera, self.rect, self.hp, self.max_hp)


class CentipedeSegment(GameObject):
    """One trailing body segment behind a Centipede's head -- purely
    visual, no hp/combat/collision of its own; the head is the only
    entity in game.robots, so it's the only thing any attacker ever
    targets or damages. `row` picks which of Centipede.png's plain
    body-segment frames (see CENTIPEDE_SEGMENT_ROWS) this segment plays,
    purely for visual variety along the body."""

    def __init__(self, game, position, row: int) -> None:
        super().__init__(name="centipede_segment")
        self.position = Vector2(position)
        self.rect.size = (SPRITE_SIZE * SCALE_FACTOR, SPRITE_SIZE * SCALE_FACTOR)
        self.rect.center = self.position

        self.add_component(SpriteRenderer2D)
        self.add_component(Animator)
        add_directional_clips(self, ImagePath("Centipede", "robots"), {"idle": row})
        self.get_component(Animator).play("idle_0")

        game.all_sprites.append(self)

    def follow(self, leader_position: Vector2) -> None:
        """Snaps toward leader_position just enough to hold
        CENTIPEDE_SEGMENT_GAP -- a chain-link constraint solved fresh each
        frame (not a spring), so segments hold a fixed distance instead of
        oscillating or drifting loose over time."""
        to_leader = leader_position - self.position
        distance = to_leader.length()
        if distance > CENTIPEDE_SEGMENT_GAP:
            self.position += to_leader.normalize() * (distance - CENTIPEDE_SEGMENT_GAP)
        self.rect.center = self.position


class Centipede(Drone):
    """The one segmented drone type: a heavy, slow siege unit (GDD role)
    whose body is a chain of CentipedeSegment instances trailing the head.
    Only the head (self) has hp/combat/wall-collision -- engage()/attack()/
    move() are all inherited from Drone unchanged; the only new behavior
    is updating the segment chain each frame and cleaning it up on death.
    Segments spawn already spaced out behind the head (not stacked on top
    of it) so an idle, undiscovered Centipede reads as a body immediately
    instead of looking like a single ball until it first moves."""

    def __init__(self, game, position) -> None:
        super().__init__(game, position, drone_type="Centipede")
        self.segments = [
            CentipedeSegment(game, Vector2(position) - Vector2(0, CENTIPEDE_SEGMENT_GAP * (i + 1)), row)
            for i, row in enumerate(CENTIPEDE_SEGMENT_ROWS)
        ]

    @override
    def update(self) -> None:
        super().update()
        if not self.active:
            return

        leader = self.position
        for segment in self.segments:
            segment.follow(leader)
            leader = segment.position

    @override
    def die(self) -> None:
        was_active = self.active
        super().die()
        if was_active and not self.active:
            for segment in self.segments:
                segment.active = False
                Explosion(self.game, segment.position)
                Smoke(self.game, segment.position)


class Scarab(Drone):
    def __init__(self, game, position) -> None:
        super().__init__(game, position, drone_type="Scarab")


class Spider(Drone):
    def __init__(self, game, position) -> None:
        super().__init__(game, position, drone_type="Spider")


class Hornet(Drone):
    def __init__(self, game, position) -> None:
        super().__init__(game, position, drone_type="Hornet")


class Wasp(Drone):
    def __init__(self, game, position) -> None:
        super().__init__(game, position, drone_type="Wasp")


# Spawn-time lookup for map.py, keyed the same as DRONE_TYPES.
DRONE_CLASSES = {"Scarab": Scarab, "Spider": Spider, "Hornet": Hornet, "Wasp": Wasp, "Centipede": Centipede}
