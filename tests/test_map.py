import pygame

from gameplay.map import Map, RockObstacle, _collider_local_rect
from util.constants import (
    FLAG_CONTEST_RADIUS, ROCK_OBSTACLE_COUNT, ROCK_OBSTACLE_FRAME_IDS, ROCK_OBSTACLE_SIZE, SCALE_FACTOR,
)


class FakePoint:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __getitem__(self, index):
        return (self.x, self.y)[index]


class FakeBoxCollider:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class FakePolygonCollider:
    def __init__(self, points):
        self.points = [FakePoint(x, y) for x, y in points]


def test_collider_local_rect_uses_box_fields_when_no_points():
    collider = FakeBoxCollider(2, 3, 10, 12)
    assert _collider_local_rect(collider) == (2, 3, 10, 12)


def test_collider_local_rect_bounds_polygon_points():
    # Mirrors a real Tiled auto-traced tile-edge polygon: points don't start
    # at (0, 0) and can dip slightly negative/past tile_size to join a
    # neighboring tile's shape seamlessly.
    collider = FakePolygonCollider([(-1, 0), (13, -0.5), (13, 15), (-1, 15)])
    assert _collider_local_rect(collider) == (-1, -0.5, 14, 15.5)


def test_map_spawns_obstacles_from_tile_colliders(game):
    Map(game)

    assert len(game.walls) > 0
    assert all(w.rect.width > 0 and w.rect.height > 0 for w in game.walls)


def test_map_spawn_objects_skips_nameless_objects(game):
    # pytmx surfaces the tileset's own per-tile collision shapes (added via
    # Tiled's tile collision editor) as nameless objects alongside the map's
    # real "flag"/"spawnPoint" objects -- spawn_objects() must not choke on
    # `obj.name is None` while filtering those out.
    Map(game)

    assert len(game.flags) > 0
    assert len(game.soldiers) == len(game.flags)
    assert len(game.robots) == len(game.flags)


def test_map_spawn_point_is_parsed_and_scaled(game):
    # Regression test: the "spawnPoint" branch used to be missing the
    # * SCALE_FACTOR the "flag" branch right above it has, so it pointed at
    # a raw tmx tile-unit coordinate instead of the actual scaled world
    # position -- off by a factor of SCALE_FACTOR from where the flag/
    # drone/soldier objects placed right next to it end up. Derives the
    # expected value from the tmx object itself rather than a hardcoded
    # literal, so repositioning "spawnPoint" in Tiled doesn't break this.
    m = Map(game)
    spawn_obj = next(obj for obj in m.tmx.objects if obj.name == "spawnPoint")
    expected = (spawn_obj.x * SCALE_FACTOR + m.tile_width / 2, spawn_obj.y * SCALE_FACTOR + m.tile_height / 2)

    assert m.spawn_point == expected


def test_map_spawn_point_does_not_collide_with_a_wall(game):
    m = Map(game)

    test_rect = pygame.Rect(0, 0, 48, 48)
    test_rect.center = m.spawn_point
    assert not any(test_rect.colliderect(w.rect) for w in game.walls)


def test_map_spawns_visible_collidable_rock_obstacles(game):
    from pygame_core.ecs.components.sprite_renderer2d import SpriteRenderer2D

    m = Map(game)

    rocks = [w for w in game.walls if isinstance(w, RockObstacle)]
    assert len(rocks) == ROCK_OBSTACLE_COUNT
    assert all(r in game.all_sprites for r in rocks)
    assert all(r.get_component(SpriteRenderer2D).image is not None for r in rocks)
    # not just decoration -- still real, collidable walls
    assert all(r in game.walls for r in rocks)


def test_rock_obstacles_never_land_on_a_compound_floor_or_overlap_walls(game):
    m = Map(game)

    rocks = [w for w in game.walls if isinstance(w, RockObstacle)]
    other_walls = [w for w in game.walls if w not in rocks]

    for rock in rocks:
        assert not m._is_compound_floor(*rock.rect.center)
        assert not any(rock.rect.colliderect(w.rect) for w in other_walls)

    for fx, fy in [(f.rect.centerx, f.rect.centery) for f in game.flags]:
        for rock in rocks:
            dist = ((rock.rect.centerx - fx) ** 2 + (rock.rect.centery - fy) ** 2) ** 0.5
            assert dist >= FLAG_CONTEST_RADIUS


def test_rock_obstacle_frame_ids_are_not_blank():
    # Regression test: ROCK_OBSTACLE_FRAME_IDS was originally picked from a
    # low-res labeled-grid thumbnail and pointed at the wrong row entirely
    # (small unrelated shard/crystal props, one of them fully blank) --
    # caught only by rendering the actual frames and checking their
    # bounding rects, which is exactly what this asserts going forward.
    import pygame
    from pygame_core.asset_path import ImagePath
    from pygame_core.sprite_sheet import SpriteSheet

    sheet = SpriteSheet.from_path(ImagePath("obstacles-and-objects", "obstacles_and_objects"))
    size = ROCK_OBSTACLE_SIZE
    for frame_id in ROCK_OBSTACLE_FRAME_IDS:
        col, row = frame_id % 16, frame_id // 16
        frame = sheet.frame(col, row, size, size)
        bounds = frame.get_bounding_rect()
        assert bounds.width > size // 2 and bounds.height > size // 2, frame_id


def test_is_compound_floor_true_inside_a_fenced_compound_false_on_open_grass(game):
    m = Map(game)

    # Every flag spawns inside its own fenced compound (Map.spawn_objects
    # places a flag + guardian drone together, and every flag sits inside a
    # room -- see GDD.md's Objectives section), so this holds for any of
    # them without depending on a hardcoded world position.
    flag = game.flags[0]
    assert m._is_compound_floor(*flag.rect.center) is True

    # Confirmed plain grass, not just "near the origin" -- (50, 50) turned
    # out to land on one of the map's own thin decorative divider lines
    # (see gameplay/map.py's Obstacle/RockObstacle docs), which render in
    # the same navy blue as a compound floor and would have made this
    # assertion fail for the wrong reason.
    assert m._is_compound_floor(100, 100) is False
