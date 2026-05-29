from pygame_core.camera import Camera


class FollowCamera(Camera):
    """pygame_core Camera plus a follow() that keeps a world point centered.

    The base Camera is an edge-scroll/zoom camera with no follow behaviour, so
    we set the (clamped) offset directly to centre the target each frame.
    """

    def follow(self, target_center) -> None:
        self._offset.x = self.rect.width / 2 - target_center[0] * self.scale
        self._offset.y = self.rect.height / 2 - target_center[1] * self.scale
        self._clamp_offset()
