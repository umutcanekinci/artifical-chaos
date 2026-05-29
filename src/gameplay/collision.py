"""AABB collision resolution against a wall GameObjectList.

Moving entities carry a `hit_rect` (pygame.Rect) and a `velocity` (Vector2).
Walls are GameObjects whose `.rect` is a Transform (a pygame.Rect subclass),
so the original spritecollide-based logic carries over by iterating the list.
"""


def is_collide(mover, other) -> bool:
    return mover.hit_rect.colliderect(other.rect)


def collide(mover, direction: str, walls) -> None:
    hits = [w for w in walls if w is not mover and is_collide(mover, w)]
    if not hits:
        return

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
