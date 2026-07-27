from pygame.math import Vector2

from gameplay.effects import (
    BigExplosion, Explosion, FloatingText, Grenade, HitSpark, HitSpatter, LaserFlash, MuzzleFlash, Smoke, Tracer,
)
from util.constants import (
    FLOATING_TEXT_DURATION_MS, FLOATING_TEXT_RISE_DISTANCE, FLOATING_TEXT_X_SPACING,
    GRENADE_FLIGHT_MS, TRACER_DURATION_MS,
)


def play_until_finished(effect, fake_ticks, step_ms=15, max_iters=200) -> None:
    """Advances fake_ticks in small steps and calls effect.update() each
    time, until it deactivates.

    Small steps matter: Animator.update() treats a single huge tick jump as
    "was paused" (see its _RESUME_AFTER_LAG_FACTOR) and just resets its
    clock without advancing frames, rather than fast-forwarding through the
    whole clip -- so jumping fake_ticks straight to a big number and calling
    update() once would never finish the animation. Real gameplay never
    makes a jump like that either; small steps are the realistic case.
    """
    for _ in range(max_iters):
        fake_ticks["t"] += step_ms
        effect.update()
        if not effect.active:
            return
    raise AssertionError("effect never finished playing")


def test_muzzle_flash_spawns_into_all_sprites_and_starts_active(game):
    m = MuzzleFlash(game, (0, 0))

    assert m in game.all_sprites
    assert m.active is True


def test_muzzle_flash_deactivates_once_its_clip_finishes_playing(game, fake_ticks):
    m = MuzzleFlash(game, (0, 0))

    m.update()
    assert m.active is True  # first frame still playing

    play_until_finished(m, fake_ticks)
    assert m.active is False


def test_hit_spark_hit_spatter_and_explosion_all_finish_and_deactivate(game, fake_ticks):
    for cls in (HitSpark, HitSpatter, Explosion, BigExplosion, LaserFlash, Smoke):
        effect = cls(game, (0, 0))
        play_until_finished(effect, fake_ticks)
        assert effect.active is False


def test_grenade_starts_at_the_attacker_and_ends_at_the_target(game, fake_ticks):
    fake_ticks["t"] = 0
    g = Grenade(game, (0, 0), (100, 0))

    assert g.rect.center == (0, 0)
    assert g in game.all_sprites


def test_grenade_lerps_toward_the_target_over_its_flight(game, fake_ticks):
    fake_ticks["t"] = 0
    g = Grenade(game, (0, 0), (100, 0))

    fake_ticks["t"] = GRENADE_FLIGHT_MS // 2
    g.update()

    assert 0 < g.rect.centerx < 100
    assert g.active is True


def test_grenade_deactivates_once_its_flight_duration_elapses(game, fake_ticks):
    fake_ticks["t"] = 0
    g = Grenade(game, (0, 0), (100, 0))

    fake_ticks["t"] = GRENADE_FLIGHT_MS
    g.update()

    assert g.active is False


def test_effects_face_the_direction_passed_in(game):
    right = MuzzleFlash(game, (0, 0), facing=0)
    left = MuzzleFlash(game, (0, 0), facing=1)

    from pygame_core.ecs.components.animator import Animator
    assert right.get_component(Animator).current_clip == "flash_0"
    assert left.get_component(Animator).current_clip == "flash_1"


def test_tracer_starts_at_the_attacker_and_ends_at_the_target(game, fake_ticks):
    fake_ticks["t"] = 0
    t = Tracer(game, (0, 0), (100, 0))

    assert t.rect.center == (0, 0)
    assert t in game.all_sprites


def test_tracer_lerps_toward_the_target_over_its_duration(game, fake_ticks):
    fake_ticks["t"] = 0
    t = Tracer(game, (0, 0), (100, 0))

    fake_ticks["t"] = TRACER_DURATION_MS // 2
    t.update()

    assert 0 < t.rect.centerx < 100
    assert t.active is True


def test_tracer_deactivates_once_its_duration_elapses(game, fake_ticks):
    fake_ticks["t"] = 0
    t = Tracer(game, (0, 0), (100, 0))

    fake_ticks["t"] = TRACER_DURATION_MS
    t.update()

    assert t.active is False


def test_floating_text_spawns_centered_on_position(game, fake_ticks):
    fake_ticks["t"] = 0
    ft = FloatingText(game, (50, 50), "+HP", (80, 220, 80))

    assert ft.rect.center == (50, 50)
    assert ft in game.all_sprites
    assert ft.name == "floating_text"


def test_floating_text_offset_index_spreads_it_sideways(game, fake_ticks):
    fake_ticks["t"] = 0
    ft = FloatingText(game, (50, 50), "+DMG", (230, 80, 80), offset_index=-1)

    assert ft.rect.centerx == 50 - FLOATING_TEXT_X_SPACING
    assert ft.rect.centery == 50


def test_floating_text_rises_over_its_duration(game, fake_ticks):
    fake_ticks["t"] = 0
    ft = FloatingText(game, (50, 50), "+SPD", (90, 170, 240))

    fake_ticks["t"] = FLOATING_TEXT_DURATION_MS // 2
    ft.update()

    assert 50 - FLOATING_TEXT_RISE_DISTANCE < ft.rect.centery < 50
    assert ft.active is True


def test_floating_text_deactivates_once_its_duration_elapses(game, fake_ticks):
    fake_ticks["t"] = 0
    ft = FloatingText(game, (50, 50), "+RATE", (240, 210, 70))

    fake_ticks["t"] = FLOATING_TEXT_DURATION_MS
    ft.update()

    assert ft.active is False
