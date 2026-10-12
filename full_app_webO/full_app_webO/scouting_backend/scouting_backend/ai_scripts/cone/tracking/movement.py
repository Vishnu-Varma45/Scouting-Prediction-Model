import math
from config import MOVEMENT_SPEED_THRESHOLD, CONE_SELECTION_RADIUS

def has_movement_started(wrist_tracker):
    _, speed = wrist_tracker.fastest_hand()
    return speed > MOVEMENT_SPEED_THRESHOLD

def _distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def detect_selected_cone(wrist_tracker, cone_positions):
    """
    cone_positions: {"Red": (x, y), "Green": (x, y), "Blue": (x, y)}
    Returns the color name of the cone whose zone a wrist has entered,
    or None if no wrist is currently inside any cone's radius.
    """
    positions = wrist_tracker.positions()
    for wrist_name, wrist_pos in positions.items():
        if wrist_pos is None:
            continue
        for color, cone_pos in cone_positions.items():
            if cone_pos is None:
                continue
            if _distance(wrist_pos, cone_pos) < CONE_SELECTION_RADIUS:
                return color, wrist_name
    return None, None
