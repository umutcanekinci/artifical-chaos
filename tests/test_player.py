from collections import defaultdict
from types import SimpleNamespace

import pygame
import pytest
from pygame.math import Vector2

import gameplay.player as player_module
from gameplay.player import Footprint, Player
from util.constants import (
    FOOTPRINT_DURATION, FRICTION, PLAYER_FIRE_COOLDOWN_MS, PLAYER_FIRE_DAMAGE, PLAYER_FIRE_RANGE,
    RANK_UP_DAMAGE_BONUS, RANK_UP_FIRE_RATE_BONUS_MS, RANK_UP_FIRE_RATE_MIN_MS, RANK_UP_HP_BONUS,
    RANK_UP_MANY_RANKS_THRESHOLD, RANK_UP_SPEED_BONUS, RANK_UP_STATS_FEW_RANKS, RANK_UP_STATS_MANY_RANKS,
)


def press(game, *keys) -> None:
    game.keys = defaultdict(bool, {k: True for k in keys})


class FakeCamera:
    """screen_to_world/world_to_screen/scaled as identities/no-ops --
    Player.aim_at_mouse()/draw_health() only need *some* consistent
    position math, not real camera projection (already covered by
    tests/test_camera.py)."""
    def screen_to_world(self, pos):
        return Vector2(pos)

    def world_to_screen(self, pos):
        return Vector2(pos)

    def scaled(self, value):
        return value


def make_shooting_player(game, x=0.0, y=0.0) -> Player:
    game.camera = FakeCamera()
    game.mouse = SimpleNamespace(position=(0, 0))
    return Player(game, (x, y))


def test_walk_up_sets_negative_y_rotation(game):
    p = Player(game, (0, 0))
    press(game, pygame.K_w)

    p.walk()

    assert p.rotation.y == -1
    assert p.rotation.x == 0
    assert p.status == "walking"


def test_walk_down_sets_positive_y_rotation(game):
    p = Player(game, (0, 0))
    press(game, pygame.K_s)

    p.walk()

    assert p.rotation.y == 1


def test_walk_left_sets_negative_x_rotation_and_faces_left(game):
    p = Player(game, (0, 0))
    press(game, pygame.K_a)

    p.walk()

    assert p.rotation.x == -1
    assert p.facing == 1


def test_walk_right_sets_positive_x_rotation_and_faces_right(game):
    p = Player(game, (0, 0))
    press(game, pygame.K_d)

    p.walk()

    assert p.rotation.x == 1
    assert p.facing == 0


def test_walk_with_no_keys_is_idle_with_zero_acceleration(game):
    p = Player(game, (0, 0))

    p.walk()

    assert p.status == "idle"
    assert p.acceleration == Vector2(0, 0)


def test_walk_diagonal_sets_normalized_acceleration_toward_ms(game):
    p = Player(game, (0, 0))
    press(game, pygame.K_d, pygame.K_s)  # right + down

    p.walk()

    assert p.status == "walking"
    assert p.acceleration.length() == pytest.approx(p.ms)


def count_footprints(game) -> int:
    return len([o for o in game.all_sprites if isinstance(o, Footprint)])


def test_walk_drops_a_footprint_only_after_the_spacing_interval(game, fake_ticks):
    # last_footprint starts at 0, and the gate is `now - last_footprint >=
    # FOOTPRINT_DURATION`, so nothing drops until the clock actually reaches
    # a full interval -- not immediately at t=0.
    p = Player(game, (0, 0))
    press(game, pygame.K_d)

    fake_ticks["t"] = 0
    p.walk()
    assert count_footprints(game) == 0

    fake_ticks["t"] = FOOTPRINT_DURATION - 1
    p.walk()
    assert count_footprints(game) == 0  # still too soon

    fake_ticks["t"] = FOOTPRINT_DURATION
    p.walk()
    assert count_footprints(game) == 1

    fake_ticks["t"] = FOOTPRINT_DURATION * 2
    p.walk()
    assert count_footprints(game) == 2


def test_footprints_alternate_feet(game, fake_ticks):
    p = Player(game, (0, 0))
    press(game, pygame.K_d)
    assert p.left_foot is True  # initial

    fake_ticks["t"] = FOOTPRINT_DURATION
    p.walk()
    assert p.left_foot is False  # first footprint flips it

    fake_ticks["t"] = FOOTPRINT_DURATION * 2
    p.walk()
    assert p.left_foot is True


def test_move_applies_friction_and_updates_position(game):
    p = Player(game, (0, 0))
    p.acceleration = Vector2(1, 0)
    game.delta_time = 1.0

    p.move()

    expected_velocity = Vector2(1, 0) * game.delta_time * p.ms
    expected_velocity -= expected_velocity * FRICTION
    assert p.velocity == expected_velocity
    assert p.position == Vector2(0, 0) + expected_velocity * game.delta_time


def test_move_travels_the_same_distance_in_opposite_directions(game):
    # Regression test: once `hit_rect` (an int-only pygame.Rect) became the
    # per-frame position accumulator, its sub-pixel remainder got truncated
    # away every frame -- asymmetrically, since repeatedly flooring `int + v`
    # advances by floor(v) per step while flooring `int - v` advances by
    # -ceil(v), so movement in the negative direction on an axis (left, up)
    # consistently outran the positive direction (right, down).
    def travel(direction: Vector2) -> float:
        p = Player(game, (100000, 100000))
        p.acceleration = Vector2(direction) * p.ms
        game.delta_time = 1 / 60
        for _ in range(120):
            p.move()
        return (p.position - Vector2(100000, 100000)).length()

    assert travel(Vector2(1, 0)) == pytest.approx(travel(Vector2(-1, 0)))
    assert travel(Vector2(0, 1)) == pytest.approx(travel(Vector2(0, -1)))


def test_move_stops_at_a_wall_instead_of_passing_through(game):
    # Regression test: `move()` used to update `self.position` unconditionally
    # from velocity, then only nudge the separate `hit_rect` for collision --
    # a nudge that was thrown away every next frame since hit_rect was reset
    # from `self.position` again, so held-key movement walked straight through
    # any wall no matter how many frames it ran for.
    class FakeWall:
        def __init__(self, rect):
            self.rect = rect

    wall = FakeWall(pygame.Rect(100, -50, 20, 100))
    game.walls = [wall]

    p = Player(game, (0, 0))
    p.acceleration = Vector2(1, 0)
    game.delta_time = 1 / 60

    for _ in range(180):  # far more time than needed to reach the wall
        p.move()

    assert p.position.x <= wall.rect.left
    assert p.hit_rect.right <= wall.rect.left + 0.1


def test_get_soldier_recruits_soldiers_within_range(game):
    from gameplay.soldier import Soldier

    p = Player(game, (0, 0))
    near = Soldier(game, (30, 0))   # distance 30 < 50
    far = Soldier(game, (200, 0))   # distance 200 >= 50

    p.get_soldier()

    assert near.is_in_army is True
    assert far.is_in_army is False


def test_squad_stance_defaults_to_engage(game):
    p = Player(game, (0, 0))
    assert p.squad_stance == "engage"


def test_toggle_squad_stance_flips_between_engage_and_guard(game):
    p = Player(game, (0, 0))

    p.toggle_squad_stance()
    assert p.squad_stance == "guard"

    p.toggle_squad_stance()
    assert p.squad_stance == "engage"


def test_toggle_squad_stance_spawns_feedback_text(game):
    from gameplay.effects import FloatingText
    p = Player(game, (0, 0))

    p.toggle_squad_stance()

    kinds = [type(o) for o in game.all_sprites]
    assert FloatingText in kinds


def test_rank_up_increments_rank(game):
    p = Player(game, (0, 0))
    assert p.rank == 0

    p.rank_up()

    assert p.rank == 1


def test_rank_up_beyond_max_rank_does_not_crash_the_icon_lookup(game):
    # Regression test: get_rank_image() used to compute its sheet column as
    # `5 + self.rank % 6`, which reaches column 10 once rank % 6 == 5 --
    # one past squad-insignia.png's last valid column (it's 240x216, i.e.
    # 10 columns @RANK_SIZE, 0-9) -- raising a subsurface ValueError. Never
    # caught before because rank_up() was dead code until Flag.update()
    # started calling it, and no test called it more than once.
    p = Player(game, (0, 0))
    for _ in range(30):  # comfortably past both the old bug (rank 5) and MAX_RANK
        p.rank_up()  # must not raise

    assert p.rank == 30


def test_rank_up_applies_bonuses_only_to_the_picked_stats(game, monkeypatch):
    monkeypatch.setattr(player_module.random, "sample", lambda pool, k: ["hp", "damage"])
    p = Player(game, (0, 0))

    p.rank_up()

    assert p.max_hp == 100 + RANK_UP_HP_BONUS
    assert p.hp == 100 + RANK_UP_HP_BONUS
    assert p.fire_damage == PLAYER_FIRE_DAMAGE + RANK_UP_DAMAGE_BONUS
    # not picked this time -- unchanged
    assert p.ms == 100
    assert p.fire_cooldown_ms == PLAYER_FIRE_COOLDOWN_MS


def test_rank_up_speed_and_fire_rate_bonuses(game, monkeypatch):
    monkeypatch.setattr(player_module.random, "sample", lambda pool, k: ["speed", "fire_rate"])
    p = Player(game, (0, 0))

    p.rank_up()

    assert p.ms == 100 + RANK_UP_SPEED_BONUS
    assert p.fire_cooldown_ms == PLAYER_FIRE_COOLDOWN_MS - RANK_UP_FIRE_RATE_BONUS_MS


def test_rank_up_fire_rate_bonus_does_not_go_below_the_floor(game, monkeypatch):
    monkeypatch.setattr(player_module.random, "sample", lambda pool, k: ["fire_rate"])
    p = Player(game, (0, 0))
    p.fire_cooldown_ms = RANK_UP_FIRE_RATE_MIN_MS + 5

    p.rank_up()

    assert p.fire_cooldown_ms == RANK_UP_FIRE_RATE_MIN_MS


def test_rank_up_picks_two_stats_when_few_ranks_are_achievable(game, monkeypatch):
    game.flags = [object()] * (RANK_UP_MANY_RANKS_THRESHOLD - 1)
    seen_k = {}
    def fake_sample(pool, k):
        seen_k["k"] = k
        return list(pool)[:k]
    monkeypatch.setattr(player_module.random, "sample", fake_sample)
    p = Player(game, (0, 0))

    p.rank_up()

    assert seen_k["k"] == RANK_UP_STATS_FEW_RANKS


def test_rank_up_picks_one_stat_when_many_ranks_are_achievable(game, monkeypatch):
    game.flags = [object()] * RANK_UP_MANY_RANKS_THRESHOLD
    seen_k = {}
    def fake_sample(pool, k):
        seen_k["k"] = k
        return list(pool)[:k]
    monkeypatch.setattr(player_module.random, "sample", fake_sample)
    p = Player(game, (0, 0))

    p.rank_up()

    assert seen_k["k"] == RANK_UP_STATS_MANY_RANKS


def test_rank_up_spawns_one_floating_text_per_stat_picked(game, monkeypatch):
    monkeypatch.setattr(player_module.random, "sample", lambda pool, k: ["hp", "damage"])
    p = Player(game, (0, 0))
    before = len(game.all_sprites)

    p.rank_up()

    new_sprites = game.all_sprites[before:]
    assert len(new_sprites) == 2
    assert all(s.name == "floating_text" for s in new_sprites)


def test_footprint_grows_then_expires(game, fake_ticks):
    fake_ticks["t"] = 0
    fp = Footprint(game, (0, 0))
    assert fp.size == 1
    assert fp.active is True

    fp.update()
    assert fp.size == 2

    fake_ticks["t"] = FOOTPRINT_DURATION * 2
    fp.update()
    assert fp.active is False


def test_shoot_does_nothing_without_the_mouse_held(game, monkeypatch):
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (False, False, False))
    p = make_shooting_player(game)
    drone = SimpleNamespace(position=Vector2(50, 0), active=True, hp=40)
    game.robots.append(drone)

    fired = p.shoot()

    assert fired is False
    assert drone.hp == 40


def test_shoot_damages_the_nearest_drone_once_off_cooldown(game, monkeypatch, fake_ticks):
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (True, False, False))
    p = make_shooting_player(game)
    drone = SimpleNamespace(position=Vector2(50, 0), active=True, hp=40)
    game.robots.append(drone)

    fake_ticks["t"] = 0
    p.shoot()
    assert drone.hp == 40  # last_attack_time starts at 0 -- same cooldown-gate pattern as everywhere else

    fake_ticks["t"] = PLAYER_FIRE_COOLDOWN_MS
    fired = p.shoot()

    assert fired is True
    assert p.status == "fire"
    assert drone.hp == 40 - 12  # PLAYER_FIRE_DAMAGE, see util/constants.py

    from gameplay.effects import HitSpark, MuzzleFlash, Tracer
    kinds = [type(o) for o in game.all_sprites]
    assert MuzzleFlash in kinds
    assert Tracer in kinds
    assert HitSpark in kinds


def test_shoot_does_not_fire_through_a_wall_and_fires_at_nothing_instead(game, monkeypatch, fake_ticks):
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (True, False, False))
    p = make_shooting_player(game)
    drone = SimpleNamespace(position=Vector2(50, 0), active=True, hp=40)
    game.robots.append(drone)
    game.walls.append(SimpleNamespace(rect=pygame.Rect(25, -10, 20, 20)))
    game.mouse.position = (50, 0)  # aim toward the (now blocked) drone

    fake_ticks["t"] = PLAYER_FIRE_COOLDOWN_MS
    p.shoot()

    assert drone.hp == 40  # blocked -- no hit landed

    from gameplay.effects import BulletImpact, MuzzleFlash, Tracer
    kinds = [type(o) for o in game.all_sprites]
    assert MuzzleFlash in kinds
    assert Tracer in kinds
    assert BulletImpact in kinds  # the same wall shows up in the aim direction too


def test_shoot_damages_the_drone_again_once_the_wall_is_no_longer_in_the_way(game, monkeypatch, fake_ticks):
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (True, False, False))
    p = make_shooting_player(game)
    drone = SimpleNamespace(position=Vector2(50, 0), active=True, hp=40)
    game.robots.append(drone)
    wall = SimpleNamespace(rect=pygame.Rect(25, -10, 20, 20))
    game.walls.append(wall)
    game.mouse.position = (50, 0)

    fake_ticks["t"] = PLAYER_FIRE_COOLDOWN_MS
    p.shoot()
    assert drone.hp == 40

    game.walls.remove(wall)
    fake_ticks["t"] = PLAYER_FIRE_COOLDOWN_MS * 2
    p.shoot()

    assert drone.hp == 40 - PLAYER_FIRE_DAMAGE


def test_shoot_ignores_drones_beyond_fire_range(game, monkeypatch, fake_ticks):
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (True, False, False))
    p = make_shooting_player(game)
    drone = SimpleNamespace(position=Vector2(PLAYER_FIRE_RANGE + 10, 0), active=True, hp=40)
    game.robots.append(drone)

    fake_ticks["t"] = PLAYER_FIRE_COOLDOWN_MS
    p.shoot()

    assert drone.hp == 40


def test_shoot_fires_at_nothing_when_no_drone_is_in_range(game, monkeypatch, fake_ticks):
    # No target -- shoot() should still fire cosmetically (MuzzleFlash +
    # Tracer) toward the mouse instead of silently doing nothing.
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (True, False, False))
    p = make_shooting_player(game)
    game.mouse.position = (50, 0)  # aim away from the player so direction isn't zero

    fake_ticks["t"] = PLAYER_FIRE_COOLDOWN_MS
    p.shoot()

    from gameplay.effects import BulletImpact, MuzzleFlash, Tracer
    kinds = [type(o) for o in game.all_sprites]
    assert MuzzleFlash in kinds
    assert Tracer in kinds
    assert BulletImpact not in kinds  # no wall in the path


def test_fire_at_nothing_drops_a_bullet_impact_on_a_wall_in_the_path(game, fake_ticks):
    p = make_shooting_player(game)
    game.mouse.position = (50, 0)
    game.walls.append(SimpleNamespace(rect=pygame.Rect(30, -10, 20, 20)))

    fake_ticks["t"] = PLAYER_FIRE_COOLDOWN_MS
    p.fire_at_nothing()

    from gameplay.effects import BulletImpact
    impacts = [o for o in game.all_sprites if isinstance(o, BulletImpact)]
    assert len(impacts) == 1
    assert impacts[0].rect.centerx == 30


def test_fire_at_nothing_respects_the_cooldown(game, fake_ticks):
    p = make_shooting_player(game)
    game.mouse.position = (50, 0)

    fake_ticks["t"] = PLAYER_FIRE_COOLDOWN_MS
    p.fire_at_nothing()
    from gameplay.effects import MuzzleFlash
    first_count = len([o for o in game.all_sprites if isinstance(o, MuzzleFlash)])

    fake_ticks["t"] = PLAYER_FIRE_COOLDOWN_MS + 1  # nowhere near the next cooldown
    p.fire_at_nothing()

    assert len([o for o in game.all_sprites if isinstance(o, MuzzleFlash)]) == first_count


def test_fire_at_nothing_does_nothing_when_aiming_exactly_at_the_player(game, fake_ticks):
    p = make_shooting_player(game)
    game.mouse.position = (0, 0)  # same as the player's own position

    fake_ticks["t"] = PLAYER_FIRE_COOLDOWN_MS
    p.fire_at_nothing()  # must not raise (Vector2.normalize() on a zero vector would)

    assert game.all_sprites == [p]  # just the player itself, no effect spawned


def test_aim_at_mouse_faces_left_when_mouse_is_left_of_the_player(game):
    p = make_shooting_player(game, x=100, y=0)
    game.mouse.position = (0, 0)  # world x=0 < player x=100

    p.aim_at_mouse()

    assert p.facing == 1


def test_aim_at_mouse_faces_right_when_mouse_is_right_of_the_player(game):
    p = make_shooting_player(game, x=0, y=0)
    game.mouse.position = (100, 0)

    p.aim_at_mouse()

    assert p.facing == 0


def test_die_sets_dead_flag_and_stops_movement(game):
    p = make_shooting_player(game)
    p.velocity = Vector2(5, 5)
    p.acceleration = Vector2(1, 1)

    p.die()

    assert p.is_dead is True
    assert p.status == "death"
    assert p.velocity == Vector2(0, 0)
    assert p.acceleration == Vector2(0, 0)


def test_die_is_idempotent(game):
    p = make_shooting_player(game)
    p.die()
    p.velocity = Vector2(3, 0)  # simulate something external nudging it

    p.die()  # must not reset state a second time

    assert p.velocity == Vector2(3, 0)


def test_update_does_nothing_once_dead(game, monkeypatch):
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda: (True, False, False))
    p = make_shooting_player(game)
    p.die()
    start_position = Vector2(p.position)
    press(game, pygame.K_d)

    p.update()

    assert p.position == start_position
    assert p.status == "death"


def test_health_fraction_at_full_hp(game):
    p = make_shooting_player(game)

    assert p.health_fraction() == 1.0


def test_health_fraction_scales_with_damage(game):
    p = make_shooting_player(game)
    p.hp = 25

    assert p.health_fraction() == 0.25


def test_health_fraction_does_not_go_negative(game):
    p = make_shooting_player(game)
    p.hp = -30  # apply_damage can overshoot past 0 on a killing blow

    assert p.health_fraction() == 0.0


def test_draw_health_does_not_error_at_various_hp_levels(game):
    p = make_shooting_player(game)
    surface = pygame.Surface((100, 100))

    for hp in (100, 50, 20, 0):
        p.hp = hp
        p.draw_health(surface, game.camera)  # must not raise


def test_draw_squad_stance_renders_something(game):
    p = make_shooting_player(game)
    surface = pygame.Surface((200, 200))
    surface.fill((0, 0, 0))

    p.draw_squad_stance(surface)

    assert pygame.transform.average_color(surface) != (0, 0, 0, 255)


def test_draw_squad_stance_reflects_the_current_stance(game):
    p = make_shooting_player(game)
    surface_engage = pygame.Surface((200, 200))
    p.draw_squad_stance(surface_engage)

    p.toggle_squad_stance()
    surface_guard = pygame.Surface((200, 200))
    p.draw_squad_stance(surface_guard)

    # Different stances render different colored text -- the two surfaces
    # shouldn't be pixel-identical.
    assert pygame.image.tobytes(surface_engage, "RGB") != pygame.image.tobytes(surface_guard, "RGB")
