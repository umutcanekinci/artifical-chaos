import pygame
from pygame.math import Vector2
from types import SimpleNamespace

from pygamine import SpatialGrid

from gameplay.collision import collide, is_collide, nearby_walls


class FakeMover:
    def __init__(self, hit_rect: pygame.Rect):
        self.hit_rect = hit_rect
        self.velocity = Vector2()


class FakeWall:
    def __init__(self, rect: pygame.Rect):
        self.rect = rect


def test_is_collide_true_when_rects_overlap():
    mover = FakeMover(pygame.Rect(0, 0, 10, 10))
    wall = FakeWall(pygame.Rect(5, 5, 10, 10))
    assert is_collide(mover, wall) is True


def test_is_collide_false_when_rects_dont_overlap():
    mover = FakeMover(pygame.Rect(0, 0, 10, 10))
    wall = FakeWall(pygame.Rect(100, 100, 10, 10))
    assert is_collide(mover, wall) is False


def test_collide_does_nothing_with_no_overlapping_walls():
    mover = FakeMover(pygame.Rect(0, 0, 10, 10))
    mover.velocity = Vector2(5, 0)
    walls = [FakeWall(pygame.Rect(100, 100, 10, 10))]

    collide(mover, "x", walls)

    assert mover.hit_rect == pygame.Rect(0, 0, 10, 10)
    assert mover.velocity == Vector2(5, 0)


def test_collide_ignores_itself_if_present_in_the_walls_list():
    mover = FakeMover(pygame.Rect(0, 0, 10, 10))
    collide(mover, "x", [mover])  # `w is not mover` guard must skip it
    assert mover.hit_rect == pygame.Rect(0, 0, 10, 10)


def test_collide_x_pushes_mover_to_the_left_of_the_wall():
    mover = FakeMover(pygame.Rect(0, 0, 10, 10))  # mover.x(0) < wall.x(5)
    mover.velocity = Vector2(3, 0)
    wall = FakeWall(pygame.Rect(5, 0, 10, 10))

    collide(mover, "x", [wall])

    assert mover.hit_rect.right == 4  # wall.left - 0.1, truncated by Rect
    assert mover.velocity.x == 0


def test_collide_x_pushes_mover_to_the_right_of_the_wall():
    mover = FakeMover(pygame.Rect(5, 0, 10, 10))  # mover.x(5) > wall.x(0), overlapping
    mover.velocity = Vector2(-3, 0)
    wall = FakeWall(pygame.Rect(0, 0, 10, 10))

    collide(mover, "x", [wall])

    assert mover.hit_rect.left == 10  # wall.right + 0.1, truncated
    assert mover.velocity.x == 0


def test_collide_y_pushes_mover_above_the_wall():
    mover = FakeMover(pygame.Rect(0, 0, 10, 10))
    mover.velocity = Vector2(0, 3)
    wall = FakeWall(pygame.Rect(0, 5, 10, 10))

    collide(mover, "y", [wall])

    assert mover.hit_rect.bottom == 4
    assert mover.velocity.y == 0


def test_collide_y_pushes_mover_below_the_wall():
    mover = FakeMover(pygame.Rect(0, 5, 10, 10))  # mover.y(5) > wall.y(0), overlapping
    mover.velocity = Vector2(0, -3)
    wall = FakeWall(pygame.Rect(0, 0, 10, 10))

    collide(mover, "y", [wall])

    assert mover.hit_rect.top == 10
    assert mover.velocity.y == 0


def test_collide_only_resolves_against_the_first_matching_wall():
    mover = FakeMover(pygame.Rect(0, 0, 10, 10))
    mover.velocity = Vector2(3, 0)
    walls = [FakeWall(pygame.Rect(5, 0, 10, 10)), FakeWall(pygame.Rect(5, 0, 10, 10))]

    collide(mover, "x", walls)  # must not raise, behaves like a single wall

    assert mover.hit_rect.right == 4


def test_nearby_walls_falls_back_to_the_plain_list_with_no_grid():
    game = SimpleNamespace(walls=[FakeWall(pygame.Rect(0, 0, 10, 10))])
    assert nearby_walls(game, pygame.Rect(0, 0, 10, 10)) is game.walls


def test_nearby_walls_queries_the_grid_when_present():
    near = FakeWall(pygame.Rect(0, 0, 10, 10))
    far = FakeWall(pygame.Rect(1000, 1000, 10, 10))
    grid = SpatialGrid.of_static([near, far], cell_size=50)
    game = SimpleNamespace(walls=[near, far], wall_grid=grid)

    result = nearby_walls(game, pygame.Rect(0, 0, 10, 10))

    assert near in result
    assert far not in result
