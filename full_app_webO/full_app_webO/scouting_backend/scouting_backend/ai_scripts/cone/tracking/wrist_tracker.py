"""
Keeps a short rolling history of wrist positions so we can compute
velocity and decide which hand is closer to a given cone.
"""
import time
from collections import deque
from config import VELOCITY_SMOOTHING_FRAMES


class WristTracker:
    def __init__(self, history_len=15):
        self.left_history = deque(maxlen=history_len)   # (x, y, t)
        self.right_history = deque(maxlen=history_len)

    def update(self, pose_result):
        now = time.time()
        if pose_result is None:
            return
        lx, ly, lv = pose_result["left_wrist"]
        rx, ry, rv = pose_result["right_wrist"]
        if lv > 0.3:
            self.left_history.append((lx, ly, now))
        if rv > 0.3:
            self.right_history.append((rx, ry, now))

    def _speed(self, history):
        if len(history) < 2:
            return 0.0
        recent = list(history)[-VELOCITY_SMOOTHING_FRAMES:]
        if len(recent) < 2:
            return 0.0
        (x0, y0, t0) = recent[0]
        (x1, y1, t1) = recent[-1]
        dt = t1 - t0
        if dt <= 0:
            return 0.0
        dist = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        return dist / dt

    def left_speed(self):
        return self._speed(self.left_history)

    def right_speed(self):
        return self._speed(self.right_history)

    def positions(self):
        """Latest known (x, y) for each wrist, or None if unseen."""
        left = self.left_history[-1][:2] if self.left_history else None
        right = self.right_history[-1][:2] if self.right_history else None
        return {"left_wrist": left, "right_wrist": right}

    def fastest_hand(self):
        ls, rs = self.left_speed(), self.right_speed()
        return ("left_wrist", ls) if ls >= rs else ("right_wrist", rs)
