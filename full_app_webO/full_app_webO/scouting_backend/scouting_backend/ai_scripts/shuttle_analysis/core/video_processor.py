"""
core/video_processor.py
========================
Wraps OpenCV video capture and exposes a frame iterator
with metadata. All downstream modules receive frames via
this class so the video is read only once.
"""

import cv2
from dataclasses import dataclass
from typing import Generator, Tuple
import numpy as np


@dataclass
class FrameData:
    index: int          # 0-based frame number
    timestamp_s: float  # seconds from start
    bgr: np.ndarray     # raw BGR frame (H, W, 3)


class VideoProcessor:
    """Thin wrapper around cv2.VideoCapture."""

    def __init__(self, video_path: str):
        self.video_path = video_path
        self._cap = cv2.VideoCapture(video_path)
        if not self._cap.isOpened():
            raise IOError(f"Cannot open video: {video_path}")

    # ── Metadata ────────────────────────────────────────────
    def get_metadata(self) -> dict:
        cap = self._cap
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        return {
            "fps": fps,
            "frame_count": frame_count,
            "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "duration": frame_count / fps if fps > 0 else 0.0,
            "fourcc": int(cap.get(cv2.CAP_PROP_FOURCC)),
        }

    # ── Frame iterator ──────────────────────────────────────
    def iter_frames(self, resize: Tuple[int, int] = None) -> Generator[FrameData, None, None]:
        """
        Yields FrameData objects for every frame in the video.

        Args:
            resize: optional (width, height) to rescale each frame.
        """
        cap = self._cap
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # rewind
        fps = cap.get(cv2.CAP_PROP_FPS)
        idx = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if resize:
                frame = cv2.resize(frame, resize)
            yield FrameData(
                index=idx,
                timestamp_s=idx / fps,
                bgr=frame,
            )
            idx += 1

    # ── Random access ───────────────────────────────────────
    def read_frame(self, frame_index: int) -> np.ndarray:
        """Read a specific frame by index (0-based)."""
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = self._cap.read()
        if not ret:
            raise ValueError(f"Cannot read frame {frame_index}")
        return frame

    def get_writer(self, output_path: str, fps: float = None) -> cv2.VideoWriter:
        """Return a VideoWriter matching the source video dimensions."""
        meta = self.get_metadata()
        _fps = fps or meta["fps"]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        return cv2.VideoWriter(
            output_path, fourcc, _fps, (meta["width"], meta["height"])
        )

    def release(self):
        self._cap.release()

    def __del__(self):
        try:
            self._cap.release()
        except Exception:
            pass
