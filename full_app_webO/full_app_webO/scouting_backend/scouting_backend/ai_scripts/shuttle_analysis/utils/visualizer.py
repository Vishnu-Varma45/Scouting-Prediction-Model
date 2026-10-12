"""
utils/visualizer.py
====================
Renders an annotated output video with:
  - Athlete bounding box
  - Speed gauge bar (top-right)
  - HUD panel (top-left): time, speed, splits, score, tier
  - Turn markers
  - Speed-profile strip (bottom 80 px)
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

from core.pose_tracker import PoseFrame


class Visualizer:

    FONT   = cv2.FONT_HERSHEY_SIMPLEX
    GREEN  = (50, 200, 50)
    YELLOW = (30, 210, 210)
    RED    = (60,  60, 230)
    WHITE  = (240, 240, 240)
    BLACK  = (10,  10,  10)
    CYAN   = (200, 200, 40)
    ORANGE = (30, 140, 255)
    PURPLE = (200,  80, 200)

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)

    # ── Main ─────────────────────────────────────────────────
    def render_annotated_video(
        self,
        video_path: str,
        pose_sequence: List[PoseFrame],
        analysis: Dict[str, Any],
        scout: Dict[str, Any],
        fps: float,
        output_name: str = "shuttle_annotated.mp4",
    ) -> str:

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise IOError(f"Cannot open: {video_path}")

        W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        out_path = str(self.output_dir / output_name)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(out_path, fourcc, fps, (W, H + 80))

        speeds   = analysis.get("speed_profile", [])
        times    = analysis.get("timestamps_s", [])
        turn_set = set(analysis.get("turn_times_s", []))
        splits   = analysis.get("split_times_s", [])
        score    = scout.get("score", 0)
        tier     = scout.get("tier", "?")

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            pf       = pose_sequence[frame_idx] if frame_idx < len(pose_sequence) else None
            speed_v  = speeds[frame_idx] if frame_idx < len(speeds) else 0.0
            ts       = times[frame_idx] if frame_idx < len(times) else 0.0

            # Bounding box
            if pf and pf.pose_detected and pf.bounding_box:
                x, y, w, h = pf.bounding_box
                col = self.GREEN if speed_v > 1.0 else self.YELLOW
                cv2.rectangle(frame, (x, y), (x + w, y + h), col, 2)
                if pf.body_center_px is not None:
                    cx, cy = int(pf.body_center_px[0]), int(pf.body_center_px[1])
                    cv2.circle(frame, (cx, cy), 4, self.ORANGE, -1)

            # HUD
            self._draw_hud(frame, speed_v, ts, splits, score, tier, W, H)

            # Turn flash
            if any(abs(ts - tts) < (1.5 / fps) for tts in turn_set):
                cv2.putText(frame, "TURN", (W // 2 - 40, 50),
                            self.FONT, 1.4, self.ORANGE, 3)

            # Speed strip
            strip = self._build_speed_strip(speeds, frame_idx, W, 80)
            combined = np.vstack([frame, strip])
            writer.write(combined)
            frame_idx += 1

        cap.release()
        writer.release()
        return out_path

    # ── HUD ──────────────────────────────────────────────────
    def _draw_hud(self, frame, speed, ts, splits, score, tier, W, H):
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (240, 200), self.BLACK, -1)
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

        lines = [
            (f"Time   : {ts:6.2f} s",    self.WHITE),
            (f"Speed  : {speed:5.2f} m/s", self.CYAN),
            (f"Legs   : {len(splits)}",   self.WHITE),
            (f"Score  : {score:.1f}/100", self.GREEN),
            (f"Tier   : {tier}",          self.GREEN),
        ]
        for i, (text, col) in enumerate(lines):
            cv2.putText(frame, text, (8, 28 + i * 30), self.FONT, 0.60, col, 2)

        # Speed bar (top-right)
        bx, by, bw, bh = W - 165, 10, 145, 18
        fill = int(bw * min(speed / 10.0, 1.0))
        bar_col = self.GREEN if speed < 5 else (self.YELLOW if speed < 8 else self.RED)
        cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), self.WHITE, 1)
        cv2.rectangle(frame, (bx, by), (bx + fill, by + bh), bar_col, -1)
        cv2.putText(frame, f"SPEED {speed:.1f}m/s", (bx, by - 4),
                    self.FONT, 0.40, self.WHITE, 1)

    # ── Speed strip ──────────────────────────────────────────
    def _build_speed_strip(self, speeds: list, cur: int, W: int, H: int) -> np.ndarray:
        strip = np.zeros((H, W, 3), dtype=np.uint8)
        if not speeds:
            return strip
        n = len(speeds)
        max_s = max(speeds) if max(speeds) > 0 else 1.0

        cv2.line(strip, (0, H // 2), (W, H // 2), (40, 40, 40), 1)

        for i in range(1, n):
            x1 = int((i - 1) / n * W)
            x2 = int(i / n * W)
            y1 = H - int(speeds[i - 1] / max_s * (H - 6)) - 3
            y2 = H - int(speeds[i]     / max_s * (H - 6)) - 3
            col = (80, 180, 80) if i != cur else self.WHITE
            cv2.line(strip, (x1, y1), (x2, y2), col, 1)

        cx = int(cur / n * W)
        cv2.line(strip, (cx, 0), (cx, H), (255, 200, 0), 2)
        cv2.putText(strip, "Speed Profile", (4, H - 4), self.FONT, 0.38, (160, 160, 160), 1)
        return strip
