"""Shared hitscan combat primitives, used by drones, the player, and soldiers.

"Hitscan" here means an instant nearest-target-in-range check, not a
directional raycast -- every attacker already computes its target the same
way Soldier.walk() always has (see gameplay/soldier.py: always freshly
computed, never cached), so reusing that same nearest-in-range primitive for
combat keeps every actor's targeting identical instead of inventing a second,
inconsistent notion of "aim". Precise directional/cone aiming is a natural
follow-up once this ships (see GDD.md).
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


def ready_to_attack(now: int, last_attack_time: int, cooldown_ms: int) -> bool:
    return now - last_attack_time >= cooldown_ms


def apply_damage(target, amount: int) -> bool:
    """Reduces target.hp by amount. Returns True if this killed it."""
    target.hp -= amount
    return target.hp <= 0
