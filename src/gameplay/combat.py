"""Shared hitscan combat primitives, used by drones, the player, and soldiers.

"Hitscan" here means an instant nearest-target-in-range check, not a
directional raycast -- every attacker already computes its target the same
way Soldier.walk() always has (see gameplay/soldier.py: always freshly
computed, never cached), so reusing that same nearest-in-range primitive for
combat keeps every actor's targeting identical instead of inventing a second,
inconsistent notion of "aim".

*Which* target gets picked is still purely range-based (find_nearest never
considers walls); *whether* a ranged attack on that target actually lands is
a separate question answered by has_line_of_sight() below, which every
ranged attacker (Drone's fire branch, Soldier.engage(), Player.shoot()) now
checks before calling attack() -- melee/splash attacks don't, since they're
already point-blank or arc over short cover. A target behind a wall is still
found and still gets faced/aimed at; the attack itself just doesn't land,
same "gate the action, not the targeting" shape as SQUAD_ATTACK_MAX_PLAYER_SPEED.
"""
from pygame.math import Vector2


def find_nearest(origin: Vector2, candidates, max_range: float):
    """Returns the closest candidate (must have `.position`; skipped if it
    has an `.active` attribute set to False) within max_range, or None."""
    nearest = None
    nearest_dist = max_range
    for candidate in candidates:
        if getattr(candidate, "active", True) is False:
            continue
        dist = (Vector2(candidate.position) - origin).length()
        if dist <= nearest_dist:
            nearest = candidate
            nearest_dist = dist
    return nearest


def find_all_in_range(origin: Vector2, candidates, max_range: float) -> list:
    """AoE counterpart to find_nearest -- every candidate (same `.position`/
    `.active` contract) within max_range of origin, not just the closest
    one. Used by Grenadier-Class's splash attack (Soldier.attack())."""
    origin = Vector2(origin)
    return [candidate for candidate in candidates
            if getattr(candidate, "active", True) is not False
            and (Vector2(candidate.position) - origin).length() <= max_range]


def raycast(origin: Vector2, direction: Vector2, max_range: float, walls):
    """Casts a ray from origin along direction up to max_range against a
    wall GameObjectList, returning the nearest intersection point (a
    Vector2) or None if nothing's hit.

    Two callers, one cosmetic and one not: Player.fire_at_nothing() uses it
    directly to decide whether a shot with no target should leave a wall
    decal (see gameplay/effects.py's BulletImpact); has_line_of_sight()
    below wraps it to gate whether a ranged attack on an already-found
    target actually lands. Uses pygame.Rect.clipline() (returns the two
    points where a line crosses a rect's edges, or an empty tuple) rather
    than hand-rolled line/AABB math; of the two returned points, the one
    nearer `origin` is the entry point.
    """
    if direction.length() == 0:
        return None
    direction = direction.normalize()
    end = origin + direction * max_range

    nearest_point = None
    nearest_dist = max_range
    for wall in walls:
        clipped = wall.rect.clipline(origin, end)
        if not clipped:
            continue
        for point in clipped:
            dist = (Vector2(point) - origin).length()
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_point = Vector2(point)
    return nearest_point


def has_line_of_sight(origin: Vector2, target_pos: Vector2, walls) -> bool:
    """Whether a straight line from origin to target_pos is unobstructed by
    any wall -- gates ranged attacks (Drone's fire branch, Soldier.engage(),
    Player.shoot()) so cover actually blocks fire instead of every hit
    resolving through walls regardless of geometry, same as BulletImpact
    already treats walls as solid for a *missed* shot. Melee/splash attacks
    don't call this -- they're already point-blank or arc over short cover.

    A thin wrapper around raycast() capped at the exact distance to the
    target, so a wall *behind* the target is never mistaken for one
    blocking it. Deliberately doesn't move an attacker toward the target to
    "solve" a blocked shot -- movement is already handled by each
    attacker's own approach-then-attack logic (see Drone.engage()), which
    falls back to walking closer whenever this returns False."""
    origin = Vector2(origin)
    target_pos = Vector2(target_pos)
    distance = (target_pos - origin).length()
    if distance == 0:
        return True
    return raycast(origin, target_pos - origin, distance, walls) is None


def ready_to_attack(now: int, last_attack_time: int, cooldown_ms: int) -> bool:
    return now - last_attack_time >= cooldown_ms


def apply_damage(target, amount: int) -> bool:
    """Reduces target.hp by amount. Returns True if this killed it."""
    target.hp -= amount
    return target.hp <= 0
