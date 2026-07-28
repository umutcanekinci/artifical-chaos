from collections import defaultdict
from types import SimpleNamespace

import pygame
import pytest
from pygame.math import Vector2

from gameplay.soldier import Soldier
from util.constants import (
    AVOID_RADIUS, FACING_DEADZONE, RADIO_OPERATOR_REINFORCEMENT_OFFSET, SOLDIER_CLASSES,
    SOLDIER_HOLD_DISTANCE, SQUAD_ATTACK_MAX_PLAYER_SPEED, SQUAD_GUARD_ENGAGE_RADIUS,
    SQUAD_GUARD_HOLD_DISTANCE,
)

ASSAULT = SOLDIER_CLASSES["Assault-Class"]
SNIPER = SOLDIER_CLASSES["Sniper-Class"]
GRENADIER = SOLDIER_CLASSES["Grenadier-Class"]
RADIO_OPERATOR = SOLDIER_CLASSES["RadioOperator-Class"]


def press(game, *keys) -> None:
    game.keys = defaultdict(bool, {k: True for k in keys})


def test_walk_faces_left_on_a_or_left_arrow(game):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))
    press(game, pygame.K_a)

    s.walk()

    assert s.facing == 1


def test_walk_faces_right_on_d_or_right_arrow(game):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))
    s.facing = 1
    press(game, pygame.K_d)

    s.walk()

    assert s.facing == 0


def test_walk_chases_the_player_when_far_enough_away(game):
    game.player = SimpleNamespace(position=Vector2(200, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))  # distance 200 > 100

    s.walk()

    assert s.status == "walking"
    assert s.acceleration.length() == pytest.approx(s.ms)
    assert s.acceleration.x > 0  # player is to the right


def test_walk_stays_idle_within_the_hold_distance(game):
    game.player = SimpleNamespace(position=Vector2(50, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))  # distance 50 <= 100

    s.walk()

    assert s.status == "idle"
    assert s.acceleration == Vector2(0, 0)


def test_move_travels_the_same_distance_in_opposite_directions(game):
    # Regression test: once `hit_rect` (an int-only pygame.Rect) became the
    # per-frame position accumulator, its sub-pixel remainder got truncated
    # away every frame -- asymmetrically, since repeatedly flooring `int + v`
    # advances by floor(v) per step while flooring `int - v` advances by
    # -ceil(v), so movement in the negative direction on an axis (left, up)
    # consistently outran the positive direction (right, down).
    def travel(direction: Vector2) -> float:
        s = Soldier(game, (100000, 100000))
        s.acceleration = Vector2(direction) * s.ms
        game.delta_time = 1 / 60
        for _ in range(120):
            s.move()
        return (s.position - Vector2(100000, 100000)).length()

    assert travel(Vector2(1, 0)) == pytest.approx(travel(Vector2(-1, 0)))
    assert travel(Vector2(0, 1)) == pytest.approx(travel(Vector2(0, -1)))


def test_move_stops_at_a_wall_instead_of_passing_through(game):
    # Regression test: `move()` used to update `self.position` unconditionally
    # from velocity, then only nudge the separate `hit_rect` for collision --
    # a nudge that was thrown away every next frame since hit_rect was reset
    # from `self.position` again, so sustained movement walked straight
    # through any wall no matter how many frames it ran for.
    class FakeWall:
        def __init__(self, rect):
            self.rect = rect

    wall = FakeWall(pygame.Rect(100, -50, 20, 100))
    game.walls = [wall]

    s = Soldier(game, (0, 0))
    s.acceleration = Vector2(1, 0)
    game.delta_time = 1 / 60

    for _ in range(180):  # far more time than needed to reach the wall
        s.move()

    assert s.position.x <= wall.rect.left
    assert s.hit_rect.right <= wall.rect.left + 0.1


def test_add_to_army_sets_the_flag(game):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))
    assert s.is_in_army is False

    s.add_to_army()

    assert s.is_in_army is True


def test_update_does_nothing_when_not_in_army(game):
    game.player = SimpleNamespace(position=Vector2(500, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))
    start_position = Vector2(s.position)

    s.update()

    assert s.position == start_position
    assert s.status == "idle"


def test_avoid_entities_pushes_away_from_nearby_soldiers(game):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    a = Soldier(game, (0, 0))
    b = Soldier(game, (10, 0))  # distance 10 < AVOID_RADIUS

    a.acceleration = Vector2(0, 0)
    a.avoid_entities()

    # a is to the left of b, so it gets pushed further left (negative x).
    assert a.acceleration.x < 0


def test_avoid_entities_ignores_soldiers_outside_the_radius(game):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    a = Soldier(game, (0, 0))
    Soldier(game, (AVOID_RADIUS + 10, 0))  # outside the avoid radius

    a.acceleration = Vector2(0, 0)
    a.avoid_entities()

    assert a.acceleration == Vector2(0, 0)


def test_avoid_entities_does_not_push_against_itself(game):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    a = Soldier(game, (0, 0))

    a.acceleration = Vector2(0, 0)
    a.avoid_entities()  # only `a` exists in game.soldiers -- must not self-push

    assert a.acceleration == Vector2(0, 0)


def test_avoid_entities_pushes_harder_the_closer_the_soldiers_are(game):
    # A constant unit-length nudge (the old behavior) shoves a soldier
    # right on top of another no harder than one barely inside the avoid
    # radius -- not enough to actually resolve a visible overlap. The push
    # strength must scale with proximity instead.
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    close = Soldier(game, (0, 0))
    Soldier(game, (5, 0))  # well inside AVOID_RADIUS

    far = Soldier(game, (100, 0))
    Soldier(game, (100 + AVOID_RADIUS - 5, 0))  # barely inside AVOID_RADIUS

    close.acceleration = Vector2(0, 0)
    close.avoid_entities()
    far.acceleration = Vector2(0, 0)
    far.avoid_entities()

    assert close.acceleration.length() > far.acceleration.length()


def test_avoid_entities_separates_exactly_overlapping_soldiers(game):
    # dist.length() == 0 for two soldiers at the exact same position --
    # Vector2.normalize() raises on a zero vector, so this must not crash,
    # and the two must push in opposite directions (not both push the same
    # way, which would keep them stuck together) so they don't stay
    # overlapping forever once they converge onto the same point.
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    a = Soldier(game, (0, 0))
    b = Soldier(game, (0, 0))

    a.acceleration = Vector2(0, 0)
    a.avoid_entities()  # must not raise
    b.acceleration = Vector2(0, 0)
    b.avoid_entities()

    assert a.acceleration != Vector2(0, 0)
    assert b.acceleration != Vector2(0, 0)
    assert a.acceleration != b.acceleration  # pushed apart, not together


def test_soldier_classes_are_all_faster_than_the_player():
    # Soldier.walk() only moves once farther than 100px from the player,
    # so a soldier slower than the player can fall behind and then never
    # catch back up, no matter how long you wait -- see util/constants.py.
    PLAYER_SPEED = 100
    for name, stats in SOLDIER_CLASSES.items():
        assert stats["speed"] > PLAYER_SPEED, name


def test_engage_fires_at_the_nearest_drone_in_range(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))
    drone = SimpleNamespace(position=Vector2(50, 0), active=True, hp=40)
    game.robots.append(drone)

    fake_ticks["t"] = ASSAULT["fire_cooldown_ms"]
    s.engage()

    assert s.status == "fire"
    assert s.acceleration == Vector2(0, 0)
    assert drone.hp == 40 - ASSAULT["fire_damage"]
    assert s.facing == 0  # drone is to the right

    from gameplay.effects import HitSpark, MuzzleFlash, Tracer
    kinds = [type(o) for o in game.all_sprites]
    assert MuzzleFlash in kinds
    assert Tracer in kinds
    assert HitSpark in kinds


def test_engage_spawns_the_muzzle_flash_offset_toward_the_target_not_on_the_soldier(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))
    drone = SimpleNamespace(position=Vector2(50, 0), active=True, hp=40)
    game.robots.append(drone)

    fake_ticks["t"] = ASSAULT["fire_cooldown_ms"]
    s.engage()

    from gameplay.effects import MuzzleFlash
    flash = next(o for o in game.all_sprites if isinstance(o, MuzzleFlash))
    assert flash.rect.centerx > s.position.x


def test_engage_does_not_fire_through_a_wall_and_follows_the_player_instead(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))
    drone = SimpleNamespace(position=Vector2(50, 0), active=True, hp=40)
    game.robots.append(drone)
    game.walls.append(SimpleNamespace(rect=pygame.Rect(25, -10, 20, 20)))

    fake_ticks["t"] = ASSAULT["fire_cooldown_ms"]
    s.engage()

    assert drone.hp == 40  # blocked -- no hit landed
    # No approach behavior of its own -- falls back to walk() (idle, since
    # the player is within hold distance), not stuck holding aim forever.
    assert s.status == "idle"


def test_engage_fires_again_once_the_wall_is_no_longer_in_the_way(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))
    drone = SimpleNamespace(position=Vector2(50, 0), active=True, hp=40)
    game.robots.append(drone)
    wall = SimpleNamespace(rect=pygame.Rect(25, -10, 20, 20))
    game.walls.append(wall)

    fake_ticks["t"] = ASSAULT["fire_cooldown_ms"]
    s.engage()
    assert drone.hp == 40

    game.walls.remove(wall)
    s.engage()

    assert drone.hp == 40 - ASSAULT["fire_damage"]
    assert s.status == "fire"


def test_engage_falls_back_to_following_the_player_with_no_drone_in_range(game):
    game.player = SimpleNamespace(position=Vector2(200, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))

    s.engage()

    assert s.status == "walking"  # same as a direct walk() call, see test_walk_chases_...


def test_engage_ignores_drones_beyond_fire_range(game):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))
    far_drone = SimpleNamespace(position=Vector2(ASSAULT["fire_range"] + 10, 0), active=True, hp=40)
    game.robots.append(far_drone)

    s.engage()

    assert far_drone.hp == 40
    assert s.status == "idle"  # falls back to walk(); player is within hold distance


def test_engage_respects_the_fire_cooldown(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))
    drone = SimpleNamespace(position=Vector2(50, 0), active=True, hp=40)
    game.robots.append(drone)

    fake_ticks["t"] = ASSAULT["fire_cooldown_ms"]
    s.engage()
    assert drone.hp == 40 - ASSAULT["fire_damage"]

    fake_ticks["t"] = ASSAULT["fire_cooldown_ms"] + 1
    s.engage()

    assert drone.hp == 40 - ASSAULT["fire_damage"]  # still on cooldown


def test_engage_does_not_attack_while_the_player_is_moving_fast(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(SQUAD_ATTACK_MAX_PLAYER_SPEED, 0),
                                  squad_stance="engage")
    s = Soldier(game, (0, 0))
    drone = SimpleNamespace(position=Vector2(50, 0), active=True, hp=40)
    game.robots.append(drone)

    fake_ticks["t"] = ASSAULT["fire_cooldown_ms"]
    s.engage()

    assert drone.hp == 40  # no hit landed...
    assert s.status == "fire"  # ...but it still holds its aim on the target
    assert s.acceleration == Vector2(0, 0)
    assert s.facing == 0


def test_engage_attacks_once_the_player_slows_back_under_the_threshold(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(SQUAD_ATTACK_MAX_PLAYER_SPEED, 0),
                                  squad_stance="engage")
    s = Soldier(game, (0, 0))
    drone = SimpleNamespace(position=Vector2(50, 0), active=True, hp=40)
    game.robots.append(drone)

    fake_ticks["t"] = ASSAULT["fire_cooldown_ms"]
    s.engage()
    assert drone.hp == 40  # blocked while moving

    game.player.velocity = Vector2(0, 0)
    s.engage()

    assert drone.hp == 40 - ASSAULT["fire_damage"]  # lands now that the player has stopped


def test_engage_attacks_normally_while_the_player_is_stationary(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(0, 0), squad_stance="engage")
    s = Soldier(game, (0, 0))
    drone = SimpleNamespace(position=Vector2(50, 0), active=True, hp=40)
    game.robots.append(drone)

    fake_ticks["t"] = ASSAULT["fire_cooldown_ms"]
    s.engage()

    assert drone.hp == 40 - ASSAULT["fire_damage"]


def test_walk_uses_a_tighter_hold_distance_in_guard_stance(game):
    # Halfway between SQUAD_GUARD_HOLD_DISTANCE and SOLDIER_HOLD_DISTANCE:
    # close enough to hold position under the normal "engage" hold distance,
    # far enough to already need to walk closer under the tighter guard one.
    midpoint = (SQUAD_GUARD_HOLD_DISTANCE + SOLDIER_HOLD_DISTANCE) / 2
    game.player = SimpleNamespace(position=Vector2(midpoint, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))

    s.walk(SOLDIER_HOLD_DISTANCE)
    assert s.status == "idle"

    s.walk(SQUAD_GUARD_HOLD_DISTANCE)
    assert s.status == "walking"


def test_engage_ignores_a_drone_far_from_the_player_in_guard_stance(game, fake_ticks):
    # A Sniper's long fire_range can reach a drone that's nowhere near the
    # player -- guard stance should refuse to chase it, even though the
    # soldier itself is well within fire_range.
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="guard")
    s = Soldier(game, (0, 0), soldier_class="Sniper-Class")
    far_drone = SimpleNamespace(position=Vector2(SQUAD_GUARD_ENGAGE_RADIUS + 10, 0), active=True, hp=200)
    game.robots.append(far_drone)
    assert (far_drone.position - game.player.position).length() <= SNIPER["fire_range"]  # in range of the soldier...

    fake_ticks["t"] = SNIPER["fire_cooldown_ms"]
    s.engage()

    assert far_drone.hp == 200  # ...but ignored anyway, too far from the commander
    assert s.status == "idle"  # falls back to walk() with the tight guard hold distance


def test_engage_still_fights_a_drone_near_the_player_in_guard_stance(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="guard")
    s = Soldier(game, (0, 0))
    drone = SimpleNamespace(position=Vector2(SQUAD_GUARD_ENGAGE_RADIUS - 10, 0), active=True, hp=40)
    game.robots.append(drone)

    fake_ticks["t"] = ASSAULT["fire_cooldown_ms"]
    s.engage()

    assert drone.hp == 40 - ASSAULT["fire_damage"]


def test_engage_facing_does_not_flip_while_crossing_directly_over_a_drone(game):
    # Regression test: see FACING_DEADZONE in util/constants.py -- delta.x
    # hovering near 0 used to flip self.facing every frame from ordinary
    # movement noise while crossing to the other side of a target.
    game.player = SimpleNamespace(position=Vector2(200, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))
    s.facing = 0
    drone = SimpleNamespace(position=Vector2(FACING_DEADZONE - 1, 100), active=True, hp=40)
    game.robots.append(drone)

    s.engage()

    assert s.facing == 0  # unchanged -- well within the deadzone


def test_soldier_defaults_to_assault_class_stats(game):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))

    assert s.ms == ASSAULT["speed"]
    assert s.fire_range == ASSAULT["fire_range"]
    assert s.fire_damage == ASSAULT["fire_damage"]
    assert s.fire_cooldown_ms == ASSAULT["fire_cooldown_ms"]


def test_soldier_class_param_picks_the_matching_stats(game):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0), soldier_class="Sniper-Class")

    assert s.ms == SNIPER["speed"]
    assert s.fire_range == SNIPER["fire_range"]
    assert s.fire_damage == SNIPER["fire_damage"]
    assert s.fire_cooldown_ms == SNIPER["fire_cooldown_ms"]


def test_sniper_fires_at_a_target_beyond_the_assault_fire_range(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0), soldier_class="Sniper-Class")
    drone = SimpleNamespace(
        position=Vector2(ASSAULT["fire_range"] + 50, 0), active=True, hp=100,
    )
    game.robots.append(drone)

    fake_ticks["t"] = SNIPER["fire_cooldown_ms"]
    s.engage()

    assert s.status == "fire"
    assert drone.hp == 100 - SNIPER["fire_damage"]


def test_grenadier_splash_damages_every_drone_near_the_target(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0), soldier_class="Grenadier-Class")
    target = SimpleNamespace(position=Vector2(100, 0), active=True, hp=100)
    clustered = SimpleNamespace(position=Vector2(100 + GRENADIER["splash_radius"] - 5, 0), active=True, hp=100)
    far = SimpleNamespace(position=Vector2(100 + GRENADIER["splash_radius"] + 50, 0), active=True, hp=100)
    game.robots.extend([target, clustered, far])

    fake_ticks["t"] = GRENADIER["fire_cooldown_ms"]
    s.engage()

    assert target.hp == 100 - GRENADIER["fire_damage"]
    assert clustered.hp == 100 - GRENADIER["fire_damage"]
    assert far.hp == 100  # outside splash_radius of the thrown-at point


def test_grenadier_splash_kills_and_deactivates_drones_at_zero_hp(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0), soldier_class="Grenadier-Class")
    target = SimpleNamespace(position=Vector2(100, 0), active=True, hp=GRENADIER["fire_damage"])
    died = []
    target.die = lambda: died.append(True)
    game.robots.append(target)

    fake_ticks["t"] = GRENADIER["fire_cooldown_ms"]
    s.engage()

    assert target.hp <= 0
    assert died == [True]


def test_grenadier_splash_never_damages_the_player_or_an_allied_soldier(game, fake_ticks):
    # No friendly fire, by design (GDD.md's Combat section) -- Grenadier's
    # splash is the one attack in the game that could otherwise catch a
    # bystander, since it hits everyone in a radius rather than one chosen
    # target. find_all_in_range is only ever called with game.robots as
    # candidates, so a player/ally standing right in the blast must still
    # come out completely unscathed.
    game.player = SimpleNamespace(position=Vector2(105, 0), velocity=Vector2(), squad_stance="engage", hp=100)  # inside the blast radius
    s = Soldier(game, (0, 0), soldier_class="Grenadier-Class")
    ally = Soldier(game, (95, 0))  # also inside the blast radius
    ally.is_in_army = True
    ally.hp = 100
    target = SimpleNamespace(position=Vector2(100, 0), active=True, hp=100)
    game.robots.append(target)

    fake_ticks["t"] = GRENADIER["fire_cooldown_ms"]
    s.engage()

    assert target.hp < 100  # the actual (opposing-faction) target was hit
    assert game.player.hp == 100
    assert ally.hp == 100


def test_engage_never_targets_another_soldier_even_one_much_closer_than_any_drone(game, fake_ticks):
    # Same no-friendly-fire guarantee as the Grenadier splash test above,
    # for the ordinary single-target path: game.robots and game.soldiers
    # are always separate candidate pools, so even a soldier standing
    # right next to the attacker (closer than any drone around) is never a
    # valid target.
    game.player = SimpleNamespace(position=Vector2(1000, 0), velocity=Vector2(), squad_stance="engage")  # far away, not a target either
    attacker = Soldier(game, (0, 0))
    ally = Soldier(game, (5, 0))  # much closer than fire_range, but a soldier, not a drone
    ally.is_in_army = True
    ally.hp = 100
    drone = SimpleNamespace(position=Vector2(50, 0), active=True, hp=40)
    game.robots.append(drone)

    fake_ticks["t"] = ASSAULT["fire_cooldown_ms"]
    attacker.engage()

    assert ally.hp == 100
    assert drone.hp == 40 - ASSAULT["fire_damage"]  # the actual drone was hit instead


def test_grenadier_attack_spawns_a_grenade_and_explosion_not_a_tracer(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0), soldier_class="Grenadier-Class")
    drone = SimpleNamespace(position=Vector2(100, 0), active=True, hp=100)
    game.robots.append(drone)

    fake_ticks["t"] = GRENADIER["fire_cooldown_ms"]
    s.engage()

    from gameplay.effects import BigExplosion, Grenade, MuzzleFlash, Smoke, Tracer
    kinds = [type(o) for o in game.all_sprites]
    assert Grenade in kinds
    assert BigExplosion in kinds
    assert Smoke in kinds  # lingers after the splash impact
    assert MuzzleFlash not in kinds  # no gun to flash for a thrown grenade
    assert Tracer not in kinds


def test_non_grenadier_classes_have_zero_splash_radius(game):
    for name, stats in SOLDIER_CLASSES.items():
        if name != "Grenadier-Class":
            assert stats["splash_radius"] == 0, name


def test_non_radio_operator_classes_have_zero_support_cooldown(game):
    for name, stats in SOLDIER_CLASSES.items():
        if name != "RadioOperator-Class":
            assert stats["support_cooldown_ms"] == 0, name


def test_radio_operator_calls_in_a_reinforcement_already_in_the_army(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    radio = Soldier(game, (0, 0), soldier_class="RadioOperator-Class")
    radio.is_in_army = True

    fake_ticks["t"] = RADIO_OPERATOR["support_cooldown_ms"]
    called = radio.call_reinforcement()

    assert called is True
    assert len(game.soldiers) == 2
    reinforcement = game.soldiers[-1]
    assert reinforcement is not radio
    assert reinforcement.is_in_army is True
    assert (Vector2(reinforcement.position) - radio.position).length() == pytest.approx(
        RADIO_OPERATOR_REINFORCEMENT_OFFSET, abs=0.5)


def test_radio_operator_reinforcements_are_never_another_radio_operator(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    radio = Soldier(game, (0, 0), soldier_class="RadioOperator-Class")
    radio.is_in_army = True

    for i in range(5):
        fake_ticks["t"] = (i + 1) * RADIO_OPERATOR["support_cooldown_ms"]
        radio.call_reinforcement()

    reinforcements = game.soldiers[1:]
    assert len(reinforcements) == 5
    assert all(s.support_cooldown_ms == 0 for s in reinforcements)


def test_radio_operator_respects_its_own_cooldown(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    radio = Soldier(game, (0, 0), soldier_class="RadioOperator-Class")
    radio.is_in_army = True

    fake_ticks["t"] = RADIO_OPERATOR["support_cooldown_ms"]
    assert radio.call_reinforcement() is True

    fake_ticks["t"] += 1
    assert radio.call_reinforcement() is False  # still on cooldown
    assert len(game.soldiers) == 2  # unchanged


def test_radio_operator_never_fights_even_with_a_drone_in_range(game, fake_ticks):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    radio = Soldier(game, (0, 0), soldier_class="RadioOperator-Class")
    radio.is_in_army = True
    drone = SimpleNamespace(position=Vector2(10, 0), active=True, hp=40)
    game.robots.append(drone)

    fake_ticks["t"] = RADIO_OPERATOR["support_cooldown_ms"]
    radio.engage()

    assert drone.hp == 40  # never attacked
    from gameplay.effects import MuzzleFlash, Tracer
    kinds = [type(o) for o in game.all_sprites]
    assert MuzzleFlash not in kinds
    assert Tracer not in kinds


class FakeCamera:
    def world_to_screen(self, pos):
        return Vector2(pos)

    def scaled(self, value):
        return value

    def scale_image(self, image):
        return image


def test_draw_health_does_not_error_when_full_or_damaged(game):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))
    surface = pygame.Surface((100, 100))

    s.draw_health(surface, FakeCamera())  # full hp -- no-op, must not raise

    s.hp = 40
    s.draw_health(surface, FakeCamera())  # damaged -- draws, must not raise


def test_draw_recruited_marker_is_a_noop_when_not_in_army(game):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))
    surface = pygame.Surface((100, 100))
    surface.fill((5, 5, 5))

    s.draw_recruited_marker(surface, FakeCamera())

    assert surface.get_at((50, 50))[:3] == (5, 5, 5)  # untouched


def test_draw_recruited_marker_draws_once_recruited(game):
    game.player = SimpleNamespace(position=Vector2(0, 0), velocity=Vector2(), squad_stance="engage")
    s = Soldier(game, (0, 0))
    s.add_to_army()
    surface = pygame.Surface((100, 100))
    surface.fill((5, 5, 5))

    s.draw_recruited_marker(surface, FakeCamera())  # must not raise
