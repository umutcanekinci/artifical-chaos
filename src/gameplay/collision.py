"""AABB collision resolution against a wall GameObjectList.

Moving entities carry a `hit_rect` (pygame.Rect) and a `velocity` (Vector2).
Walls are GameObjects whose `.rect` is a Transform (a pygame.Rect subclass),
so the original spritecollide-based logic carries over by iterating the list.
"""


def nearby_walls(game, hit_rect):
    """Candidate walls for a collision check against `hit_rect`, narrowed to
    game.wall_grid's nearby cells (pygamine.util.spatial_grid.SpatialGrid) instead
    of scanning every wall on the map. Walls are static for a run's lifetime
    (Map() builds them all before Game.restart() ever calls update()), so the
    grid is built once per restart rather than every frame -- see
    Game.restart(). Falls back to the plain wall list when no grid is set
    (tests construct Player/Soldier/Drone against a bare FakeGame with no
    wall_grid), same convention standoff's Entity.move() already uses.

    Callers query once per move() call (not once per axis) and inflate by a
    full cell on every side, since a mover can cross into an adjacent cell
    within the same frame's movement."""
    grid = getattr(game, "wall_grid", None)
    if grid is None:
        return game.walls
    area = hit_rect.inflate(grid.cell_size * 2, grid.cell_size * 2)
    return list(grid.query_rect(area))


def is_collide(mover, other) -> bool:
    return mover.hit_rect.colliderect(other.rect)


def collide(mover, direction: str, walls) -> bool:
    """Returns whether a wall was actually pushed against on this axis.

    Callers should only fold `hit_rect` (a `pygame.Rect`, integer-only) back
    into their own float `position` when this returns True -- doing it
    unconditionally every frame, even with no wall in range, re-truncates a
    sub-pixel-per-frame position to an int on every call, and does so
    asymmetrically (`floor` on the way in, `ceil` on the way back out), which
    made movement visibly faster in the negative direction than the positive
    one on the same axis.
    """
    hits = [w for w in walls if w is not mover and is_collide(mover, w)]
    if not hits:
        return False

    wall = hits[0].rect

    if direction == 'x':
        if mover.hit_rect.x < wall.x:
            mover.hit_rect.right = wall.left - 0.1
        else:
            mover.hit_rect.left = wall.right + 0.1
        mover.velocity.x = 0

    elif direction == 'y':
        if mover.hit_rect.y < wall.y:
            mover.hit_rect.bottom = wall.top - 0.1
        else:
            mover.hit_rect.top = wall.bottom + 0.1
        mover.velocity.y = 0

    return True
