"""
Finds colored cones in a frame using simple HSV thresholding.
Used only during CALIBRATION to lock in cone positions. After
calibration the app trusts the stored (x, y) positions and does not
need to keep re-detecting cones every frame.
"""
import cv2
import numpy as np
from config import COLOR_RANGES, MIN_CONE_CONTOUR_AREA


def _mask_for_color(hsv_frame, color_name):
    ranges = COLOR_RANGES[color_name]
    mask = None
    for lower, upper in ranges:
        lower = np.array(lower, dtype=np.uint8)
        upper = np.array(upper, dtype=np.uint8)
        part = cv2.inRange(hsv_frame, lower, upper)
        mask = part if mask is None else cv2.bitwise_or(mask, part)

    # clean up noise
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)
    return mask


def find_cone(frame_bgr, color_name):
    """
    Returns (x, y) center of the largest blob matching color_name,
    or None if nothing big enough was found.
    """
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    mask = _mask_for_color(hsv, color_name)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < MIN_CONE_CONTOUR_AREA:
        return None

    M = cv2.moments(largest)
    if M["m00"] == 0:
        return None

    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])
    return (cx, cy)


def find_all_cones(frame_bgr):
    """Returns {color_name: (x, y) or None} for every configured color."""
    return {color: find_cone(frame_bgr, color) for color in COLOR_RANGES}
