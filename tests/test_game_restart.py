"""Game.restart() in isolation -- Map/Player/Tutorial/FollowCamera are
monkeypatched to lightweight stand-ins so this avoids constructing a real
Game() (which loads the real Tiled map and assets), matching
tests/test_game_end_conditions.py's / test_game_handle_event.py's approach.
The real thing is covered end-to-end by scripts/smoke_test.py."""
from types import SimpleNamespace

import app.game as game_module
from app.game import Game


class FakeRect:
    def __init__(self):
        self.width = 800
        self.height = 600
        self.center = (400, 300)


class FakeMap:
    def __init__(self, game):
        self.game = game
        self.rect = FakeRect()


class FakePlayer:
    def __init__(self, game, position):
        self.game = game
        self.position = position


class FakeTutorial:
    def __init__(self, game):
        self.game = game


class FakeCamera:
    def __init__(self, rect, *, map_width, map_height):
        self.rect = rect
        self.map_width = map_width
        self.map_height = map_height


def patch_subsystems(monkeypatch):
    monkeypatch.setattr(game_module, "Map", FakeMap)
    monkeypatch.setattr(game_module, "Player", FakePlayer)
    monkeypatch.setattr(game_module, "Tutorial", FakeTutorial)
    monkeypatch.setattr(game_module, "FollowCamera", FakeCamera)


def make_fake_game():
    return SimpleNamespace(size=(800, 600))


def test_restart_clears_the_game_over_state(monkeypatch):
    patch_subsystems(monkeypatch)
    fake = make_fake_game()
    fake.game_over = True
    fake.end_message = "GAME OVER"

    Game.restart(fake)

    assert fake.game_over is False
    assert fake.end_message == ""


def test_restart_rebuilds_entity_lists_and_subsystems(monkeypatch):
    patch_subsystems(monkeypatch)
    fake = make_fake_game()

    Game.restart(fake)

    assert fake.all_sprites == []
    assert fake.walls == []
    assert fake.flags == []
    assert fake.soldiers == []
    assert fake.robots == []
    assert isinstance(fake.map, FakeMap)
    assert isinstance(fake.player, FakePlayer)
    assert isinstance(fake.tutorial, FakeTutorial)
    assert isinstance(fake.camera, FakeCamera)


def test_restart_positions_the_player_and_camera_from_the_fresh_map(monkeypatch):
    patch_subsystems(monkeypatch)
    fake = make_fake_game()

    Game.restart(fake)

    assert fake.player.position == fake.map.rect.center
    assert fake.camera.map_width == fake.map.rect.width
    assert fake.camera.map_height == fake.map.rect.height


def test_restart_is_safe_to_call_repeatedly(monkeypatch):
    patch_subsystems(monkeypatch)
    fake = make_fake_game()

    Game.restart(fake)
    first_map = fake.map
    Game.restart(fake)

    assert fake.game_over is False
    assert fake.map is not first_map  # a genuinely fresh Map, not reused
