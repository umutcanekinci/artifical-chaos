import pygame
import pytest
from pygame.math import Vector2

from gameplay.robot import Centipede, DRONE_CLASSES, Drone, Hornet, Scarab, Spider, Wasp
from util.constants import (
    AGGRO_RADIUS, CENTIPEDE_SEGMENT_GAP, CENTIPEDE_SEGMENT_ROWS, DESTROYED_DURATION_MS, DRONE_TYPES,
    FACING_DEADZONE,
)

SCARAB = DRONE_TYPES["Scarab"]
SPIDER = DRONE_TYPES["Spider"]
HORNET = DRONE_TYPES["Hornet"]
WASP = DRONE_TYPES["Wasp"]
CENTIPEDE = DRONE_TYPES["Centipede"]


def make_scarab(game, x=0, y=0) -> Scarab:
    return Scarab(game, (x, y))


def test_spawns_idle_with_full_hp(game):
    game.player.position = Vector2(9999, 9999)  # far away -- nothing to aggro onto
    s = make_scarab(game)

    s.engage()

    assert s.hp == SCARAB["hp"]
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
        s = make_scarab(game, 100000, 100000)
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

    s = make_scarab(game)
    s.acceleration = Vector2(1, 0)
    game.delta_time = 1 / 60

    for _ in range(180):  # far more time than needed to reach the wall
        s.move()

    assert s.position.x <= wall.rect.left
    assert s.hit_rect.right <= wall.rect.left + 0.1


def test_ignores_targets_outside_aggro_radius(game):
    game.player.position = Vector2(AGGRO_RADIUS + 50, 0)
    s = make_scarab(game)

    assert s.get_target() is None


def test_get_target_never_considers_another_drone(game):
    # No friendly fire, by design (GDD.md's Combat section) -- get_target()'s
    # candidate pool is always [player] + in-army soldiers, never game.robots
    # itself, so an ally drone standing right next to this one (much closer
    # than the player, who's out of aggro range entirely here) is never a
    # valid target.
    game.player.position = Vector2(AGGRO_RADIUS + 50, 0)  # out of range
    s = make_scarab(game)
    ally = Scarab(game, (5, 0))  # much closer than AGGRO_RADIUS, but a drone

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


def test_die_spawns_lingering_smoke_alongside_the_explosion(game, fake_ticks):
    from gameplay.effects import Smoke

    s = make_scarab(game)
    s.die()

    assert any(isinstance(o, Smoke) for o in game.all_sprites)


def test_centipede_die_spawns_smoke_at_every_segment_too(game, fake_ticks):
    from gameplay.effects import Smoke

    c = Centipede(game, (0, 0))
    c.die()

    smokes = [o for o in game.all_sprites if isinstance(o, Smoke)]
    # one for the head + one per segment
    assert len(smokes) == 1 + len(c.segments)


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
        "Scarab": Scarab, "Spider": Spider, "Hornet": Hornet, "Wasp": Wasp, "Centipede": Centipede,
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


def test_hornet_kites_away_when_a_target_closes_inside_its_stand_off_range(game, fake_ticks):
    game.player.position = Vector2(HORNET["stand_off_range"] - 10, 0)  # inside stand_off_range
    game.player.hp = 100
    h = Hornet(game, (0, 0))

    fake_ticks["t"] = HORNET["fire_cooldown_ms"]
    h.engage()

    assert h.status == "fire"  # still fires while kiting
    assert game.player.hp == 100 - HORNET["fire_damage"]
    assert h.acceleration.x < 0  # backs away from the target, to its left


def test_hornet_holds_ground_when_a_target_is_outside_its_stand_off_range(game, fake_ticks):
    game.player.position = Vector2(HORNET["stand_off_range"] + 10, 0)  # outside stand_off_range, inside fire_range
    game.player.hp = 100
    h = Hornet(game, (0, 0))

    fake_ticks["t"] = HORNET["fire_cooldown_ms"]
    h.engage()

    assert h.status == "fire"
    assert h.acceleration == Vector2(0, 0)  # holds position like every other drone at fire range


def test_non_hornet_drones_have_zero_stand_off_range(game):
    for name, stats in DRONE_TYPES.items():
        if name != "Hornet":
            assert stats["stand_off_range"] == 0, name


def test_hornet_and_wasp_fire_a_laser_flash_not_a_muzzle_flash(game, fake_ticks):
    from gameplay.effects import LaserFlash, MuzzleFlash

    game.player.position = Vector2(1, 0)
    game.player.hp = 100

    for cls, stats in ((Hornet, HORNET), (Wasp, WASP)):
        game.all_sprites.clear()
        d = cls(game, (0, 0))
        fake_ticks["t"] = stats["fire_cooldown_ms"]
        d.engage()

        kinds = [type(o) for o in game.all_sprites]
        assert LaserFlash in kinds, cls.__name__
        assert MuzzleFlash not in kinds, cls.__name__


def test_scarab_spider_and_centipede_still_fire_a_muzzle_flash(game, fake_ticks):
    from gameplay.effects import LaserFlash, MuzzleFlash

    # Outside melee_range for all three (40/50/45) but inside fire_range
    # (250/90/200), so each one fires instead of meleeing.
    game.player.position = Vector2(60, 0)
    game.player.hp = 100

    for cls, stats in ((Scarab, SCARAB), (Spider, SPIDER), (Centipede, CENTIPEDE)):
        game.all_sprites.clear()
        d = cls(game, (0, 0))
        fake_ticks["t"] = stats["fire_cooldown_ms"]
        d.engage()

        kinds = [type(o) for o in game.all_sprites]
        assert MuzzleFlash in kinds, cls.__name__
        assert LaserFlash not in kinds, cls.__name__


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


def test_centipede_spawns_with_one_segment_per_configured_row(game):
    c = Centipede(game, (0, 0))

    assert len(c.segments) == len(CENTIPEDE_SEGMENT_ROWS)
    assert all(s in game.all_sprites for s in c.segments)
    assert c not in c.segments
    # not independently targetable/damageable -- only the head goes in robots
    assert all(s not in game.robots for s in c.segments)


def test_centipede_segments_spawn_already_spread_out_behind_the_head(game):
    # Regression: segments used to all spawn stacked exactly on the head's
    # position, so an idle Centipede that never moved looked like a single
    # ball instead of a body until it first walked somewhere.
    c = Centipede(game, (0, 0))

    centers = [Vector2(0, 0)] + [Vector2(s.position) for s in c.segments]
    for a, b in zip(centers, centers[1:]):
        assert (a - b).length() == pytest.approx(CENTIPEDE_SEGMENT_GAP)


def test_centipede_segment_follow_holds_the_gap_once_the_leader_moves_away(game):
    from gameplay.robot import CentipedeSegment

    seg = CentipedeSegment(game, position=(0, 0), row=CENTIPEDE_SEGMENT_ROWS[0])
    seg.follow(Vector2(1000, 0))

    assert seg.position.x == pytest.approx(1000 - CENTIPEDE_SEGMENT_GAP)


def test_centipede_segment_follow_does_nothing_within_the_gap(game):
    from gameplay.robot import CentipedeSegment

    seg = CentipedeSegment(game, position=(0, 0), row=CENTIPEDE_SEGMENT_ROWS[0])
    leader = Vector2(CENTIPEDE_SEGMENT_GAP - 1, 0)

    seg.follow(leader)

    assert seg.position == Vector2(0, 0)


def test_centipede_update_moves_the_whole_chain_as_the_head_walks(game):
    # Within AGGRO_RADIUS (400) so it chases, but beyond fire_range (200) so
    # it just walks the whole time -- never close enough to attack or stop.
    game.player.position = Vector2(300, 0)
    c = Centipede(game, (0, 0))
    before = [Vector2(s.position) for s in c.segments]

    game.delta_time = 1 / 60
    for _ in range(120):
        c.update()

    after = [Vector2(s.position) for s in c.segments]
    assert all(a != b for a, b in zip(before, after))  # every segment actually moved
    # still holding the chain together, in order, behind the head
    chain = [c.position] + after
    for a, b in zip(chain, chain[1:]):
        assert (a - b).length() == pytest.approx(CENTIPEDE_SEGMENT_GAP, abs=1.0)


def test_centipede_die_deactivates_every_segment_too(game):
    c = Centipede(game, (0, 0))

    c.die()

    assert c.active is False
    assert all(not s.active for s in c.segments)


def test_centipede_die_is_idempotent_and_does_not_re_kill_segments(game):
    c = Centipede(game, (0, 0))
    c.die()
    for s in c.segments:
        s.active = True  # simulate something external reviving them, to prove die() won't re-touch them

    c.die()  # already inactive -- must not run the segment-killing branch again

    assert all(s.active for s in c.segments)


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
