import pygame
from pygame.math import Vector2

from gameplay.robot import DRONE_CLASSES, Drone, Hornet, Scarab, Spider, Wasp
from util.constants import AGGRO_RADIUS, DESTROYED_DURATION_MS, DRONE_TYPES, FACING_DEADZONE

SCARAB = DRONE_TYPES["Scarab"]
SPIDER = DRONE_TYPES["Spider"]
HORNET = DRONE_TYPES["Hornet"]
WASP = DRONE_TYPES["Wasp"]


def make_scarab(game, x=0, y=0) -> Scarab:
    return Scarab(game, (x, y))


def test_spawns_idle_with_full_hp(game):
    game.player.position = Vector2(9999, 9999)  # far away -- nothing to aggro onto
    s = make_scarab(game)

    s.engage()

    assert s.hp == SCARAB["hp"]
    assert s.status == "idle"
    assert s.acceleration == Vector2(0, 0)


def test_ignores_targets_outside_aggro_radius(game):
    game.player.position = Vector2(AGGRO_RADIUS + 50, 0)
    s = make_scarab(game)

    assert s.get_target() is None


def test_chases_the_player_within_aggro_but_outside_fire_range(game):
    game.player.position = Vector2(SCARAB["fire_range"] + 50, 0)
    s = make_scarab(game)

    s.engage()

    assert s.status == "walking"
    assert s.acceleration.length() > 0
    assert s.facing == 0  # target is to the right


def test_fires_when_in_fire_range_but_outside_melee_range(game, fake_ticks):
    game.player.position = Vector2(SCARAB["fire_range"] - 10, 0)
    game.player.hp = 100
    s = make_scarab(game)

    fake_ticks["t"] = SCARAB["fire_cooldown_ms"]  # past the initial cooldown
    s.engage()

    assert s.status == "fire"
    assert s.acceleration == Vector2(0, 0)
    assert game.player.hp < 100

    from gameplay.effects import HitSpatter, MuzzleFlash, Tracer
    kinds = [type(o) for o in game.all_sprites]
    assert MuzzleFlash in kinds
    assert Tracer in kinds
    assert HitSpatter in kinds


def test_melees_within_melee_range(game, fake_ticks):
    game.player.position = Vector2(SCARAB["melee_range"] - 5, 0)
    game.player.hp = 100
    s = make_scarab(game)

    fake_ticks["t"] = SCARAB["melee_cooldown_ms"]
    s.engage()

    assert s.status == "melee"
    assert game.player.hp == 100 - SCARAB["melee_damage"]

    # Melee has no gun to flash and nothing to fly across the map -- only
    # a hit effect at the target, no MuzzleFlash/Tracer (see Drone.attack()).
    from gameplay.effects import HitSpatter, MuzzleFlash, Tracer
    kinds = [type(o) for o in game.all_sprites]
    assert MuzzleFlash not in kinds
    assert Tracer not in kinds
    assert HitSpatter in kinds


def test_die_spawns_an_explosion(game, fake_ticks):
    from gameplay.effects import Explosion

    s = make_scarab(game)
    s.die()

    assert any(isinstance(o, Explosion) for o in game.all_sprites)


def test_facing_does_not_flip_while_crossing_directly_over_the_target(game):
    # Regression test: delta.x hovering near 0 while an enemy crosses to the
    # other side of its target used to flip self.facing every frame from
    # ordinary movement noise, flickering the mirrored sprite -- see
    # FACING_DEADZONE in util/constants.py.
    s = make_scarab(game, x=0, y=0)
    s.facing = 0
    game.player.position = Vector2(FACING_DEADZONE - 1, 100)  # almost directly below

    s.engage()

    assert s.facing == 0  # unchanged -- well within the deadzone


def test_facing_still_flips_for_a_real_horizontal_difference(game):
    s = make_scarab(game, x=0, y=0)
    s.facing = 0
    game.player.position = Vector2(-(FACING_DEADZONE + 1), 100)

    s.engage()

    assert s.facing == 1


def test_prefers_the_nearer_soldier_over_a_farther_player(game):
    from gameplay.soldier import Soldier

    game.player.position = Vector2(300, 0)
    soldier = Soldier(game, (50, 0))
    soldier.add_to_army()
    s = make_scarab(game)

    assert s.get_target() is soldier


def test_drone_classes_registry_maps_names_to_the_matching_subclass():
    assert DRONE_CLASSES == {
        "Scarab": Scarab, "Spider": Spider, "Hornet": Hornet, "Wasp": Wasp,
    }


def test_spider_uses_its_own_stats_and_is_a_drone(game):
    s = Spider(game, (0, 0))

    assert isinstance(s, Drone)
    assert s.hp == SPIDER["hp"]
    assert s.ms == SPIDER["speed"]
    assert s.fire_range == SPIDER["fire_range"]


def test_spider_melees_a_target_within_its_own_shorter_melee_range(game, fake_ticks):
    game.player.position = Vector2(SPIDER["melee_range"] - 5, 0)
    game.player.hp = 100
    s = Spider(game, (0, 0))

    fake_ticks["t"] = SPIDER["melee_cooldown_ms"]
    s.engage()

    assert s.status == "melee"
    assert game.player.hp == 100 - SPIDER["melee_damage"]


def test_die_holds_the_destroyed_status_before_deactivating(game, fake_ticks):
    s = make_scarab(game)

    fake_ticks["t"] = 0
    s.die()
    assert s.status == "destroyed"
    assert s.active is True

    s.update()
    assert s.active is True  # not enough time has passed yet

    fake_ticks["t"] = DESTROYED_DURATION_MS
    s.update()
    assert s.active is False


def test_die_is_idempotent(game, fake_ticks):
    s = make_scarab(game)
    fake_ticks["t"] = 100
    s.die()
    first_death_time = s.death_time

    fake_ticks["t"] = 200
    s.die()  # must not reset the timer if already destroyed

    assert s.death_time == first_death_time


def test_hornet_never_melees_even_at_point_blank_range(game, fake_ticks):
    # melee_range is 0 for Hornet -- distance <= 0 never happens, so it
    # should always fire (or chase) instead, never melee.
    game.player.position = Vector2(1, 0)
    game.player.hp = 100
    h = Hornet(game, (0, 0))

    fake_ticks["t"] = HORNET["fire_cooldown_ms"]
    h.engage()

    assert h.status == "fire"
    assert game.player.hp == 100 - HORNET["fire_damage"]


def test_wasp_has_only_one_animation_frame_set_reused_for_every_status(game):
    # Wasp's sheet only has one animation row -- every clip_rows entry
    # points at row 0, so idle/walking/fire/melee are all built from the
    # same source frames (just distinct clip objects with the same pixels).
    import pygame
    from pygame_core.ecs.components.animator import Animator

    w = Wasp(game, (0, 0))
    clips = w.get_component(Animator).clips

    assert set(clips) == {"idle_0", "idle_1", "walking_0", "walking_1",
                           "fire_0", "fire_1", "melee_0", "melee_1"}
    as_bytes = lambda frames: [pygame.image.tobytes(f, "RGBA") for f in frames]
    assert as_bytes(clips["idle_0"].frames) == as_bytes(clips["fire_0"].frames)


def test_hornet_and_wasp_are_removed_immediately_on_death_with_no_destroyed_hold(game):
    h = Hornet(game, (0, 0))
    w = Wasp(game, (0, 0))

    h.die()
    w.die()

    assert h.active is False
    assert w.active is False


def test_hornet_die_is_idempotent(game):
    h = Hornet(game, (0, 0))

    h.die()
    h.die()  # must not error on a second call once already inactive

    assert h.active is False


class FakeCamera:
    def world_to_screen(self, pos):
        return Vector2(pos)

    def scaled(self, value):
        return value


def test_draw_health_does_not_error_when_full_or_damaged(game):
    s = make_scarab(game)
    surface = pygame.Surface((100, 100))

    s.draw_health(surface, FakeCamera())  # full hp -- no-op, must not raise

    s.hp = 10
    s.draw_health(surface, FakeCamera())  # damaged -- draws, must not raise


def test_draw_health_is_skipped_once_destroyed(game, fake_ticks):
    s = make_scarab(game)
    s.die()
    surface = pygame.Surface((100, 100))

    s.draw_health(surface, FakeCamera())  # must not draw a bar over a wreck -- must not raise either way
