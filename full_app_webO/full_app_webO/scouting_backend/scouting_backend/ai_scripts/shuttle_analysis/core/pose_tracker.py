"""
core/pose_tracker.py
=====================
Motion tracker using OpenCV background subtraction + contour analysis.
Works without any external model downloads.

For environments where mediapipe model files are available, see the
mediapipe_pose_tracker.py companion file.
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Optional

from core.video_processor import VideoProcessor


@dataclass
class PoseFrame:
    frame_index: int
    timestamp_s: float
    # Body centre in pixel coords
    body_center_px: Optional[np.ndarray]  # (x, y)
    bounding_box: Optional[tuple]          # (x, y, w, h)
    # Per-frame flags
    pose_detected: bool = False
    direction: str = "unknown"   # "left" | "right"
    speed_m_s: float = 0.0
    contour_area: float = 0.0


class PoseTracker:
    """
    Tracks athlete motion across frames using OpenCV background subtraction.
    Returns a list of PoseFrame objects compatible with ShuttleAnalyzer.
    """

    def __init__(
        self,
        min_detection_confidence: float = 0.5,   # kept for API compatibility
        min_tracking_confidence: float = 0.5,
        min_contour_area: float = 500,
        history: int = 200,
        var_threshold: float = 40,
    ):
        self.min_contour_area = min_contour_area
        self._fgbg = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=var_threshold,
            detectShadows=False,
        )
        self._kernel = np.ones((7, 7), np.uint8)

    # ── Public API ──────────────────────────────────────────
    def process_video(self, processor: VideoProcessor) -> List[PoseFrame]:
        sequence: List[PoseFrame] = []

        for fd in processor.iter_frames():
            mask = self._fgbg.apply(fd.bgr)
            mask = cv2.dilate(mask, self._kernel, iterations=2)

            cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            pf = PoseFrame(
                frame_index=fd.index,
                timestamp_s=fd.timestamp_s,
                body_center_px=None,
                bounding_box=None,
                pose_detected=False,
            )

            if cnts:
                c = max(cnts, key=cv2.contourArea)
                area = cv2.contourArea(c)
                if area >= self.min_contour_area:
                    M = cv2.moments(c)
                    if M["m00"] > 0:
                        cx = float(M["m10"] / M["m00"])
                        cy = float(M["m01"] / M["m00"])
                        x, y, w, h = cv2.boundingRect(c)
                        pf.body_center_px = np.array([cx, cy], dtype=np.float32)
                        pf.bounding_box = (x, y, w, h)
                        pf.pose_detected = True
                        pf.contour_area = float(area)

            sequence.append(pf)

        self._smooth_positions(sequence)
        self._assign_directions(sequence)
        return sequence

    # ── Smoothing ───────────────────────────────────────────
    @staticmethod
    def _smooth_positions(sequence: List[PoseFrame], window: int = 11):
        valid = [(i, pf) for i, pf in enumerate(sequence) if pf.pose_detected]
        if len(valid) < window:
            return
        xs = np.array([pf.body_center_px[0] for _, pf in valid])
        ys = np.array([pf.body_center_px[1] for _, pf in valid])
        from scipy.signal import savgol_filter
        wl = window if window % 2 == 1 else window + 1
        wl = min(wl, len(xs) if len(xs) % 2 == 1 else len(xs) - 1)
        xs_sm = savgol_filter(xs, wl, 2)
        ys_sm = savgol_filter(ys, wl, 2)
        for j, (i, pf) in enumerate(valid):
            sequence[i].body_center_px = np.array([xs_sm[j], ys_sm[j]], dtype=np.float32)

    # ── Direction assignment ─────────────────────────────────
    @staticmethod
    def _assign_directions(sequence: List[PoseFrame]):
        valid = [(i, pf) for i, pf in enumerate(sequence) if pf.pose_detected]
        for j in range(1, len(valid)):
            prev_x = valid[j - 1][1].body_center_px[0]
            curr_x = valid[j][1].body_center_px[0]
            direction = "right" if curr_x > prev_x else "left"
            sequence[valid[j][0]].direction = direction
