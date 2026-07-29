import random

import pygame
import pytmx
from pygame.math import Vector2

from pygamine.tilemap import TiledMap
from pygamine.ecs.game_object import GameObject
from pygamine.ecs.components.sprite_renderer2d import SpriteRenderer2D
from pygamine.sprite_sheet import SpriteSheet
from pygamine.image import scale_by
from pygamine.asset_path import ImagePath

from util.constants import *
from gameplay.flag import Flag
from gameplay.robot import DRONE_CLASSES
from gameplay.soldier import Soldier


class Obstacle(GameObject):
    """Invisible collision wall — Transform only, no renderer."""

    def __init__(self, game, position, size) -> None:
        super().__init__(name="obstacle")
        self.rect.size = size
        self.rect.topleft = position
        game.walls.append(self)


class RockObstacle(GameObject):
    """A visible, collidable rock — unlike Obstacle (Transform-only,
    invisible), this doubles as real decoration: a real sprite from
    obstacles-and-objects.png, picked randomly per instance from
    ROCK_OBSTACLE_FRAME_IDS for variety, plus a `.rect` that
    gameplay/collision.py's `collide()` blocks against exactly like any
    other wall (RockObstacle instances go in `game.walls` too)."""

    _sheet: SpriteSheet | None = None

    def __init__(self, game, position, frame_id: int) -> None:
        super().__init__(name="rock")
        if RockObstacle._sheet is None:
            RockObstacle._sheet = SpriteSheet.from_path(
                ImagePath("obstacles-and-objects", "obstacles_and_objects"))

        size = ROCK_OBSTACLE_SIZE
        col, row = frame_id % 16, frame_id // 16
        image = scale_by(RockObstacle._sheet.frame(col, row, size, size), SCALE_FACTOR)

        self.rect.size = (size * SCALE_FACTOR, size * SCALE_FACTOR)
        self.rect.center = position
        self.add_component(SpriteRenderer2D).set_image(image)

        game.all_sprites.append(self)
        game.walls.append(self)


def _collider_local_rect(collider) -> tuple[float, float, float, float]:
    """Bounding box (x, y, width, height) of one Tiled per-tile collision
    shape, in tile-local pixel space. Tiled's tile collision editor mostly
    produces polygons (auto-traced around a tile's opaque pixels, so they
    often extend a little past the tile's own 0..tile_size bounds to join
    seamlessly with a neighboring tile of the same formation) rather than
    plain boxes, so this reads `.points` when present instead of assuming
    `.width`/`.height` are populated."""
    points = getattr(collider, "points", None)
    if points:
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        min_x, min_y = min(xs), min(ys)
        return min_x, min_y, max(xs) - min_x, max(ys) - min_y
    return collider.x, collider.y, collider.width, collider.height


class Map(TiledMap):
    """Tiled map for Artificial Chaos: pre-renders the tile layers scaled by
    SCALE_FACTOR and spawns world entities from the object layer."""

    def __init__(self, game):
        super().__init__(str(ImagePath("tiledmap", "tileset", "tmx")))
        self.game = game

        self.tile_width = self.tile_size * SCALE_FACTOR
        self.tile_height = self.tile_size * SCALE_FACTOR
        self.image = pygame.transform.scale_by(self.pre_render(alpha=True), SCALE_FACTOR)
        self.rect = self.image.get_rect()

        # Overwritten by spawn_objects() if the tmx has a "spawnPoint"
        # object (it always should -- see the "spawn" objectgroup); None by
        # default just so a map that somehow lacks one fails loudly at
        # Player construction instead of silently on a typo'd attribute.
        self.spawn_point = None

        self.spawn_objects()
        self.spawn_tile_colliders()
        self.spawn_decorative_obstacles()

    def spawn_objects(self) -> None:
        # Two passes: the tmx's object order doesn't guarantee the
        # "spawnPoint" object comes before every "flag" one, but ranking
        # flags into FLAG_TIERS bands (see _rank_flag_tier_indices) needs
        # spawn_point known first, so gather everything before spawning
        # anything.
        soldier_classes = list(SOLDIER_CLASSES)
        flag_objs = []
        spawn_point = None

        for obj in self.tmx.objects:
            # Tiled's per-tile collision shapes (added in the tileset's own
            # tile collision editor) surface here too as nameless objects —
            # pytmx's map parser walks the whole XML tree for `objectgroup`
            # nodes before it knows which ones are tileset-embedded, so an
            # embedded tileset's `<tile><objectgroup>` colliders end up
            # looking like map-level object layers. Skip anything nameless.
            if obj.name is None:
                continue

            if "flag" in obj.name:
                flag_objs.append(obj)
            elif "spawnPoint" in obj.name:
                spawn_point = (obj.x * SCALE_FACTOR + self.tile_width / 2,
                              obj.y * SCALE_FACTOR + self.tile_height / 2)

        self.spawn_point = spawn_point
        band_indices = self._rank_flag_tier_indices(flag_objs, spawn_point)

        # Guardian drones cycle within their own flag's tier pool (round-
        # robin per band, not globally) so each tier still reads as varied
        # rather than every Outpost flag getting an identical guardian;
        # soldiers stay a single global round-robin -- tiers are a drone/
        # spawner-difficulty concept only, not a soldier one.
        tier_pool_counters = [0] * len(FLAG_TIERS)

        for flag_index, (obj, band) in enumerate(zip(flag_objs, band_indices)):
            x = obj.x * SCALE_FACTOR + self.tile_width / 2
            y = obj.y * SCALE_FACTOR + self.tile_height / 2
            tier = FLAG_TIERS[band]
            Flag(self.game, (x, y), tier=tier)

            pool = tier["drone_pool"]
            drone_class = DRONE_CLASSES[pool[tier_pool_counters[band] % len(pool)]]
            tier_pool_counters[band] += 1
            drone_class(self.game, (x, y))

            soldier_class = soldier_classes[flag_index % len(soldier_classes)]
            Soldier(self.game, (x, y + 100), soldier_class=soldier_class)

    def _rank_flag_tier_indices(self, flag_objs, spawn_point) -> list[int]:
        """Ranks flag_objs by distance from spawn_point into len(FLAG_TIERS)
        roughly-equal bands, nearest first (e.g. 10 flags / 3 tiers gives
        bands of sizes 4/3/3) -- see FLAG_TIERS in util/constants.py.
        Returns one FLAG_TIERS index per flag_obj, in the same order as
        flag_objs (not sorted by distance), so callers can zip it straight
        back against flag_objs. Falls back to the middle tier for every
        flag if spawn_point is somehow missing (every real map has one --
        see CLAUDE.md's spawnPoint note) rather than crashing."""
        band_count = len(FLAG_TIERS)
        if spawn_point is None or not flag_objs:
            return [band_count // 2] * len(flag_objs)

        def world_pos(obj) -> Vector2:
            return Vector2(obj.x * SCALE_FACTOR + self.tile_width / 2,
                          obj.y * SCALE_FACTOR + self.tile_height / 2)

        sp = Vector2(spawn_point)
        by_distance = sorted(range(len(flag_objs)),
                             key=lambda i: (world_pos(flag_objs[i]) - sp).length_squared())

        band_of = [0] * len(flag_objs)
        for rank, flag_i in enumerate(by_distance):
            band_of[flag_i] = min(rank * band_count // len(flag_objs), band_count - 1)
        return band_of

    def spawn_tile_colliders(self) -> None:
        """Spawn an Obstacle for every placed tile whose gid carries a Tiled
        tile-collision shape — drawn once, per-tile, in Tiled's own tile
        collision editor (no custom property needed; pytmx parses these
        natively into `tile_properties[gid]["colliders"]`). Replaces the old
        approach of hand-drawing a matching rectangle object over every
        wall tile: painting a tile with a collider shape is now enough.
        One Obstacle per shape's bounding box, since gameplay/collision.py
        only resolves against axis-aligned rects, not arbitrary polygons."""
        local_rects_by_gid = {
            gid: [_collider_local_rect(collider) for collider in colliders]
            for gid, colliders in self.tmx.get_tile_colliders()
        }
        if not local_rects_by_gid:
            return

        for layer in self.tmx.visible_layers:
            if not isinstance(layer, pytmx.TiledTileLayer):
                continue
            for x, y, gid in layer.iter_data():
                for local_x, local_y, width, height in local_rects_by_gid.get(gid, ()):
                    world_x = (x * self.tile_size + local_x) * SCALE_FACTOR
                    world_y = (y * self.tile_size + local_y) * SCALE_FACTOR
                    Obstacle(self.game, (world_x, world_y), (width * SCALE_FACTOR, height * SCALE_FACTOR))

    def _is_compound_floor(self, x: float, y: float) -> bool:
        """True if the map's pre-rendered pixel at (x, y) looks like a
        fenced compound's navy floor tile rather than open grass. Checking
        the actual rendered pixel color (rather than the tile's gid) sidesteps
        pytmx's internal gid remapping -- the raw XML gid for this floor tile
        (146) turns out not to match pytmx's own internal numbering for the
        same cell, confirmed by comparing the two directly, so gid-based
        matching would silently never fire. The compound floor is
        blue-dominant (sampled ~(6, 34, 109)) where grass and every other
        tile used so far are not (grass samples ~(31, 99, 99)) -- except the
        map's own thin decorative divider lines (a separate ground-layer
        tile pattern, unrelated to any wall), which happen to render in the
        same navy and so also read as True here. That's a feature, not a
        bug, for this method's only caller (spawn_decorative_obstacles): a
        rock shouldn't spawn on top of one of those either, and this is a
        rejection filter, not a precise "which tile is this" classifier."""
        color = self.image.get_at((int(x), int(y)))
        return color.b > color.r + 40 and color.b > color.g + 40

    def spawn_decorative_obstacles(self) -> None:
        """Scatters visible, collidable RockObstacles across open ground.
        Positions are chosen here at load time (not encoded in the tmx,
        unlike every other spawn method above) with a fixed seed for
        reproducibility, rejecting any candidate that overlaps an existing
        wall, falls within FLAG_CONTEST_RADIUS of any flag, or lands on a
        fenced compound's floor tile (_is_compound_floor) -- a compound's
        open interior wouldn't collide with the rect-overlap check alone,
        since only each room's perimeter is a wall, and can extend well
        past FLAG_CONTEST_RADIUS from any single flag inside it."""
        rng = random.Random(ROCK_OBSTACLE_SEED)
        margin = self.tile_width * 10
        rock_size = ROCK_OBSTACLE_SIZE * SCALE_FACTOR
        placed_rects = [obj.rect for obj in self.game.walls]
        flag_positions = [Vector2(f.rect.center) for f in self.game.flags]

        placed = 0
        attempts = 0
        while placed < ROCK_OBSTACLE_COUNT and attempts < 2000:
            attempts += 1
            x = rng.uniform(margin, self.rect.width - margin)
            y = rng.uniform(margin, self.rect.height - margin)
            if any((Vector2(x, y) - fp).length() < FLAG_CONTEST_RADIUS for fp in flag_positions):
                continue
            if self._is_compound_floor(x, y):
                continue
            candidate = pygame.Rect(0, 0, rock_size, rock_size)
            candidate.center = (x, y)
            if any(candidate.colliderect(rect) for rect in placed_rects):
                continue

            frame_id = rng.choice(ROCK_OBSTACLE_FRAME_IDS)
            rock = RockObstacle(self.game, (x, y), frame_id)
            placed_rects.append(rock.rect)
            placed += 1

    def draw_grid(self, surface: pygame.Surface, camera):
        for column_number in range(self.cols + 1):
            x = column_number * self.tile_width
            start = camera.world_to_screen((x, 0))
            end = camera.world_to_screen((x, self.rect.height))
            pygame.draw.line(surface, pygame.color.THECOLORS['grey'], start, end, 1)

        for row_number in range(self.rows + 1):
            y = row_number * self.tile_height
            start = camera.world_to_screen((0, y))
            end = camera.world_to_screen((self.rect.width, y))
            pygame.draw.line(surface, pygame.color.THECOLORS['grey'], start, end, 1)
