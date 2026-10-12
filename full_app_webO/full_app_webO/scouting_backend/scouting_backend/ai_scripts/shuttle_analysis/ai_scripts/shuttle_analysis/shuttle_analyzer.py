import cv2
import numpy as np
import json
import csv
import os
import sys
import time
from scipy.signal import savgol_filter
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple
import argparse
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
CONE_DISTANCE_METERS = 9.144          # 30 feet in metres
CONE_ZONE_FRACTION   = 0.12           # fraction of frame width = cone zone radius
MIN_SPLIT_SECONDS    = 0.8            # ignore splits shorter than this (human minimum)
MAX_REALISTIC_SPEED  = 11.0           # m/s  (~39.6 km/h) hard cap
MAX_REALISTIC_ACCEL  = 15.0           # m/s²  hard cap
SMOOTHING_WINDOW     = 11             # frames for moving average
SAVGOL_WINDOW        = 15             # Savitzky-Golay window (must be odd, > polyorder)
SAVGOL_POLY          = 3             # Savitzky-Golay polynomial order
CONE_DWELL_FRAMES    = 5             # frames athlete must stay near cone to register

# Colours (BGR)
COL_GREEN  = (0, 220, 80)
COL_RED    = (0, 60, 220)
COL_YELLOW = (0, 215, 255)
COL_WHITE  = (255, 255, 255)
COL_DARK   = (20, 20, 20)
COL_ORANGE = (0, 140, 255)
COL_BLUE   = (220, 100, 0)


# ─────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────
@dataclass
class FrameData:
    frame_idx: int
    timestamp:  float
    hip_x_px:   float
    hip_y_px:   float
    hip_x_m:    float       # real-world metres after calibration
    hip_x_m_smooth: float
    speed_ms:   float       # smoothed speed
    accel_ms2:  float       # smoothed acceleration
    body_lean:  float       # degrees
    cone_event: str         # "CONE_A" | "CONE_B" | "" 

@dataclass
class ShuttleEvent:
    event_type: str          # "START" | "CONE_A" | "CONE_B" | "FINISH"
    frame_idx:  int
    timestamp:  float
    split_time: float        # seconds since last event

@dataclass
class AnalysisResult:
    total_shuttles: int
    total_time_s:   float
    splits:         List[float]
    peak_speed_ms:  float
    avg_speed_ms:   float
    peak_accel_ms2: float
    avg_decel_ms2:  float
    score:          float
    events:         List[ShuttleEvent]
    frames:         List[FrameData]
    calibration_px_per_m: float


# ─────────────────────────────────────────────
# POSE TRACKER
# ─────────────────────────────────────────────
class PoseTracker:
  
    def __init__(self, min_contour_area: float = 500):
        self.min_contour_area = min_contour_area
        self._fgbg = cv2.createBackgroundSubtractorMOG2(
            history=200, varThreshold=40, detectShadows=False
        )
        self._kernel = np.ones((7, 7), np.uint8)
        self._last_centroid = None   # (x, y) in pixels
        self._last_bbox = None       # (x, y, w, h)

    def process(self, frame_rgb):
       
        bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        mask = self._fgbg.apply(bgr)
        mask = cv2.dilate(mask, self._kernel, iterations=2)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        centroid, bbox = None, None
        if cnts:
            c = max(cnts, key=cv2.contourArea)
            if cv2.contourArea(c) >= self.min_contour_area:
                M = cv2.moments(c)
                if M["m00"] > 0:
                    cx = M["m10"] / M["m00"]
                    cy = M["m01"] / M["m00"]
                    centroid = (cx, cy)
                    bbox = cv2.boundingRect(c)

        self._last_centroid = centroid
        self._last_bbox = bbox
        return centroid is not None

    def get_hip_midpoint(self, results, frame_w, frame_h):
        if not results or self._last_centroid is None:
            return None, None
        return self._last_centroid

    def get_body_lean(self, results, frame_w, frame_h):
       
        if not results or self._last_bbox is None:
            return 0.0
        _, _, w, h = self._last_bbox
        if h <= 0:
            return 0.0
        ratio = w / h
        angle = np.degrees(np.arctan2(max(ratio - 0.4, 0.0), 1.0))
        return round(angle, 1)

    def close(self):
        pass


# ─────────────────────────────────────────────
# CALIBRATION
# ─────────────────────────────────────────────
class ConeCalibrator:
    
    def __init__(self, frame_w: int):
        self.frame_w = frame_w
        # Cones placed roughly at 10% and 90% of frame width by default.
        # Will be updated from real athlete trajectory.
        self.cone_a_px = frame_w * 0.10
        self.cone_b_px = frame_w * 0.90
        self.px_per_m  = (self.cone_b_px - self.cone_a_px) / CONE_DISTANCE_METERS
        self.calibrated = False

    def update_from_trajectory(self, x_positions: List[float]):
        """Refine cone positions from real observed x-range."""
        if len(x_positions) < 10:
            return
        arr = np.array(x_positions)
        # Use 2nd and 98th percentile to avoid outliers
        lo = np.percentile(arr, 2)
        hi = np.percentile(arr, 98)
        span = hi - lo
        if span < 20:   # pixels — too narrow, skip
            return
        self.cone_a_px = lo
        self.cone_b_px = hi
        self.px_per_m  = span / CONE_DISTANCE_METERS
        self.calibrated = True

    def px_to_m(self, x_px: float) -> float:
        return (x_px - self.cone_a_px) / self.px_per_m


# ─────────────────────────────────────────────
# TRAJECTORY SMOOTHER  (Phase 2)
# ─────────────────────────────────────────────
def smooth_trajectory(x_arr: np.ndarray) -> np.ndarray:
    """Moving average then Savitzky-Golay filter."""
    if len(x_arr) < SMOOTHING_WINDOW + 2:
        return x_arr
    # Step 1: moving average
    kernel = np.ones(SMOOTHING_WINDOW) / SMOOTHING_WINDOW
    ma = np.convolve(x_arr, kernel, mode='same')
    # Step 2: Savitzky-Golay
    win = min(SAVGOL_WINDOW, len(ma) if len(ma) % 2 == 1 else len(ma) - 1)
    if win < SAVGOL_POLY + 2:
        return ma
    sg = savgol_filter(ma, win, SAVGOL_POLY)
    return sg


def compute_speed_accel(x_smooth: np.ndarray, timestamps: np.ndarray,
                         px_per_m: float, fps: float):
   
    n = len(x_smooth)
    speed  = np.zeros(n)
    accel  = np.zeros(n)
    x_m    = x_smooth / px_per_m

    for i in range(1, n - 1):
        dt = timestamps[i+1] - timestamps[i-1]
        if dt < 1e-6:
            continue
        speed[i] = abs(x_m[i+1] - x_m[i-1]) / dt

    # Smooth speed too
    if n > SMOOTHING_WINDOW + 2:
        speed = savgol_filter(speed, min(SAVGOL_WINDOW, n if n % 2 == 1 else n-1), SAVGOL_POLY)

    for i in range(1, n - 1):
        dt = timestamps[i+1] - timestamps[i-1]
        if dt < 1e-6:
            continue
        accel[i] = (speed[i+1] - speed[i-1]) / dt

    # Cap unrealistic values
    speed = np.clip(speed, 0, MAX_REALISTIC_SPEED)
    accel = np.clip(accel, -MAX_REALISTIC_ACCEL, MAX_REALISTIC_ACCEL)
    return speed, accel


# ─────────────────────────────────────────────
# CONE EVENT DETECTOR  (Phase 1 — the big fix)
# ─────────────────────────────────────────────
class ConeEventDetector:
    
    def __init__(self, cone_a_px: float, cone_b_px: float, frame_w: int, fps: float):
        self.cone_a_px = cone_a_px
        self.cone_b_px = cone_b_px
        self.zone_radius = frame_w * CONE_ZONE_FRACTION
        self.fps         = fps
        self.min_frames_between = int(MIN_SPLIT_SECONDS * fps)

        self.last_cone     = None          # "A" or "B" — last cone touched
        self.last_cone_frame = -9999
        self.dwell_counter = 0             # frames athlete stays in zone
        self.in_zone       = None          # current zone ("A", "B", or None)

        self.events: List[ShuttleEvent] = []
        self.last_event_frame = 0
        self.last_event_time  = 0.0

    def _in_cone_a_zone(self, x: float) -> bool:
        return x <= self.cone_a_px + self.zone_radius

    def _in_cone_b_zone(self, x: float) -> bool:
        return x >= self.cone_b_px - self.zone_radius

    def update(self, frame_idx: int, timestamp: float, x_smooth: float) -> str:
        """Call each frame. Returns event string or ''."""
        event_str = ""

        # Determine which zone athlete is in
        in_a = self._in_cone_a_zone(x_smooth)
        in_b = self._in_cone_b_zone(x_smooth)
        current_zone = "A" if in_a else ("B" if in_b else None)

        # Entered a new zone?
        if current_zone and current_zone != self.in_zone:
            self.dwell_counter = 1
            self.in_zone = current_zone
        elif current_zone == self.in_zone and current_zone is not None:
            self.dwell_counter += 1
        else:
            self.in_zone = None
            self.dwell_counter = 0

        # Register cone touch when athlete has dwelled CONE_DWELL_FRAMES
        if self.dwell_counter == CONE_DWELL_FRAMES and self.in_zone is not None:
            cone = self.in_zone
            frames_since_last = frame_idx - self.last_event_frame
            if frames_since_last >= self.min_frames_between:
                # Must alternate cones
                if self.last_cone is None or self.last_cone != cone:
                    split = timestamp - self.last_event_time
                    event_type = f"CONE_{cone}"
                    ev = ShuttleEvent(
                        event_type=event_type,
                        frame_idx=frame_idx,
                        timestamp=timestamp,
                        split_time=split if self.events else 0.0
                    )
                    self.events.append(ev)
                    self.last_cone        = cone
                    self.last_event_frame = frame_idx
                    self.last_event_time  = timestamp
                    event_str = event_type

        return event_str


# ─────────────────────────────────────────────
# ANNOTATED VIDEO WRITER  (Phase 4)
# ─────────────────────────────────────────────
class VideoAnnotator:
    def __init__(self, out_path: str, frame_w: int, frame_h: int, fps: float):
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(out_path, fourcc, fps, (frame_w, frame_h))
        self.frame_w = frame_w
        self.frame_h = frame_h

    def _draw_rounded_rect(self, img, x1, y1, x2, y2, color, alpha=0.55, radius=8):
        overlay = img.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
        cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 1)

    def _put_text(self, img, text, x, y, scale=0.52, color=COL_WHITE, thickness=1):
        cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_DUPLEX,
                    scale, COL_DARK, thickness + 2, cv2.LINE_AA)
        cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_DUPLEX,
                    scale, color, thickness, cv2.LINE_AA)

    def annotate(self, frame: np.ndarray, fd: FrameData,
                 cone_a_px: float, cone_b_px: float,
                 zone_rad: float, splits: List[float],
                 current_cone: str) -> np.ndarray:
        h, w = frame.shape[:2]

        # ── Cone zones ──────────────────────────────
        ca = int(cone_a_px)
        cb = int(cone_b_px)
        zr = int(zone_rad)

        # Cone A (left) — green pillar
        cv2.rectangle(frame, (ca - zr, 0), (ca + zr, h),
                      (0, 180, 60), 1)
        overlay = frame.copy()
        cv2.rectangle(overlay, (ca - zr, 0), (ca + zr, h), (0, 180, 60), -1)
        cv2.addWeighted(overlay, 0.12, frame, 0.88, 0, frame)
        self._put_text(frame, "CONE A", ca - 28, h - 10, 0.45, COL_GREEN)

        # Cone B (right) — red pillar
        cv2.rectangle(frame, (cb - zr, 0), (cb + zr, h),
                      (60, 60, 220), 1)
        overlay = frame.copy()
        cv2.rectangle(overlay, (cb - zr, 0), (cb + zr, h), (60, 60, 220), -1)
        cv2.addWeighted(overlay, 0.12, frame, 0.88, 0, frame)
        self._put_text(frame, "CONE B", cb - 28, h - 10, 0.45, COL_RED)

        # Cone markers
        cv2.line(frame, (ca, 0), (ca, h), COL_GREEN, 2)
        cv2.line(frame, (cb, 0), (cb, h), COL_RED, 2)

        # ── Hip dot ──────────────────────────────────
        hx = int(fd.hip_x_px)
        hy = int(fd.hip_y_px)
        cv2.circle(frame, (hx, hy), 10, COL_YELLOW, -1)
        cv2.circle(frame, (hx, hy), 10, COL_WHITE, 2)

        # ── Top-left stats panel ─────────────────────
        panel_w = 240
        panel_h = 195
        self._draw_rounded_rect(frame, 8, 8, 8 + panel_w, 8 + panel_h, COL_DARK, 0.6)

        lines = [
            (f"Frame   : {fd.frame_idx:>5}",        COL_WHITE),
            (f"Time    : {fd.timestamp:>6.2f} s",   COL_WHITE),
            (f"Speed   : {fd.speed_ms:>5.2f} m/s",  COL_GREEN),
            (f"Accel   : {fd.accel_ms2:>+6.2f} m/s²", COL_YELLOW if fd.accel_ms2 >= 0 else COL_RED),
            (f"Lean    : {fd.body_lean:>5.1f}°",    COL_ORANGE),
            (f"Cone    : {current_cone if current_cone else '—':>6}", COL_BLUE),
        ]
        for i, (txt, col) in enumerate(lines):
            self._put_text(frame, txt, 14, 30 + i * 27, 0.50, col)

        # ── Splits panel (right side) ─────────────────
        if splits:
            sp_w = 200
            sp_lines = min(len(splits), 6)
            sp_h = 30 + sp_lines * 24 + 10
            sx1 = w - sp_w - 8
            self._draw_rounded_rect(frame, sx1, 8, w - 8, 8 + sp_h, COL_DARK, 0.6)
            self._put_text(frame, "SPLITS", sx1 + 8, 28, 0.50, COL_YELLOW)
            for i, sp in enumerate(splits[-6:]):
                self._put_text(frame, f"  #{i+1}  {sp:.3f} s",
                               sx1 + 8, 50 + i * 24, 0.47, COL_WHITE)

        # ── Cone event flash ─────────────────────────
        if fd.cone_event:
            label = f"✦ {fd.cone_event} TOUCH"
            lw = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 0.9, 2)[0][0]
            lx = (w - lw) // 2
            self._draw_rounded_rect(frame, lx - 12, h//2 - 30,
                                    lx + lw + 12, h//2 + 16, (0, 180, 220), 0.75)
            self._put_text(frame, label, lx, h//2 + 8, 0.9, COL_WHITE, 2)

        # ── Speed bar ────────────────────────────────
        bar_max_speed = 10.0
        bar_w = 180
        bar_h = 14
        bx = 8
        by = 8 + panel_h + 8
        cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), COL_DARK, -1)
        fill = int(bar_w * min(fd.speed_ms / bar_max_speed, 1.0))
        bar_col = COL_GREEN if fd.speed_ms < 6 else (COL_YELLOW if fd.speed_ms < 9 else COL_RED)
        cv2.rectangle(frame, (bx, by), (bx + fill, by + bar_h), bar_col, -1)
        cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), COL_WHITE, 1)
        self._put_text(frame, "Speed", bx + bar_w + 6, by + 12, 0.40, COL_WHITE)

        return frame

    def write(self, frame):
        self.writer.write(frame)

    def close(self):
        self.writer.release()


# ─────────────────────────────────────────────
# SCOUT SCORER
# ─────────────────────────────────────────────
def compute_scout_score(result: AnalysisResult) -> float:
    
    score = 0.0

    # 1. Total time for shuttle (lower = better)
    # Pro benchmark: sub-4.4s for 30ft shuttle; poor = 6.5s+
    if result.total_time_s > 0:
        time_score = max(0, min(40, 40 * (6.5 - result.total_time_s) / (6.5 - 4.4)))
        score += time_score

    # 2. Peak speed (higher = better, up to 9 m/s)
    speed_score = max(0, min(25, 25 * result.peak_speed_ms / 9.0))
    score += speed_score

    # 3. Change of direction quality (fewer false events = better splits)
    valid_splits = [s for s in result.splits if s >= MIN_SPLIT_SECONDS]
    if valid_splits:
        avg_split = np.mean(valid_splits)
        # sub-2s split = excellent, 3.5s+ = poor
        split_score = max(0, min(20, 20 * (3.5 - avg_split) / (3.5 - 2.0)))
        score += split_score

    # 4. Shuttle count (should be 1–6 for a proper drill)
    shuttle_count = result.total_shuttles
    if 1 <= shuttle_count <= 6:
        score += 15
    elif shuttle_count <= 10:
        score += 8
    else:
        score += 0   # too many = noise

    return round(min(score, 100), 1)


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────
def analyze_video(video_path: str, output_dir: str = "output") -> AnalysisResult:
    os.makedirs(output_dir, exist_ok=True)
    basename = os.path.splitext(os.path.basename(video_path))[0]

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")

    fps      = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_w  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h  = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    print(f"\n{'='*55}")
    print(f"  SHUTTLE RUN ANALYZER")
    print(f"{'='*55}")
    print(f"  Video   : {os.path.basename(video_path)}")
    print(f"  FPS     : {fps:.1f}")
    print(f"  Size    : {frame_w}x{frame_h}")
    print(f"  Frames  : {total_frames}")
    print(f"  Cone Δ  : 30 ft = {CONE_DISTANCE_METERS} m")
    print(f"{'='*55}\n")

    tracker  = PoseTracker()
    calibrator = ConeCalibrator(frame_w)

    print("[1/3] Detecting body position for every frame...")
    per_frame_hx, per_frame_hy, per_frame_lean = {}, {}, {}
    raw_x_positions, raw_timestamps, raw_frame_indices = [], [], []

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    fi = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        ts = fi / fps
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        res = tracker.process(rgb)
        hx, hy = tracker.get_hip_midpoint(res, frame_w, frame_h)
        lean = tracker.get_body_lean(res, frame_w, frame_h)
        per_frame_lean[fi] = lean
        if hx is not None:
            per_frame_hx[fi] = hx
            per_frame_hy[fi] = hy
            raw_x_positions.append(hx)
            raw_timestamps.append(ts)
            raw_frame_indices.append(fi)
        fi += 1
    actual_frame_count = fi

    # Calibrate from real trajectory
    calibrator.update_from_trajectory(raw_x_positions)
    print(f"  Calibration: {calibrator.px_per_m:.2f} px/m  "
          f"(Cone A @ {calibrator.cone_a_px:.0f}px, Cone B @ {calibrator.cone_b_px:.0f}px)")

    # ── Pass 2: smooth + compute speed/accel ─────────
    print("[2/3] Smoothing trajectory and computing kinematics...")
    if len(raw_x_positions) < 5:
        raise ValueError("Not enough body detections in this video. "
                          "Try a clip with better contrast between the "
                          "athlete and the background.")

    x_arr  = np.array(raw_x_positions)
    ts_arr = np.array(raw_timestamps)
    x_smooth = smooth_trajectory(x_arr)
    speed_arr, accel_arr = compute_speed_accel(x_smooth, ts_arr,
                                                calibrator.px_per_m, fps)

    # Map original frame index -> position in the smoothed arrays
    pose_idx_map = {f: i for i, f in enumerate(raw_frame_indices)}

    # Event detector now has calibrated cone positions
    detector = ConeEventDetector(
        cone_a_px = calibrator.cone_a_px,
        cone_b_px = calibrator.cone_b_px,
        frame_w   = frame_w,
        fps       = fps
    )

    # ── Pass 3: annotate + event detection ───────────
    print("[3/3] Generating annotated video...")
    out_video_path = os.path.join(output_dir, f"{basename}_annotated.mp4")
    annotator = VideoAnnotator(out_video_path, frame_w, frame_h, fps)

    frame_data_list: List[FrameData] = []
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    fi = 0
    current_cone_label = ""
    splits: List[float] = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        ts = fi / fps
        hx   = per_frame_hx.get(fi)
        hy   = per_frame_hy.get(fi)
        lean = per_frame_lean.get(fi, 0.0)

        if hx is not None and fi in pose_idx_map:
            pidx = pose_idx_map[fi]
            xs   = x_smooth[pidx]
            spd  = speed_arr[pidx]
            acc  = accel_arr[pidx]
            xm   = calibrator.px_to_m(xs)
            event_str = detector.update(fi, ts, xs)
            if event_str:
                current_cone_label = event_str
                # Record split
                if detector.events and len(detector.events) >= 2:
                    splits.append(detector.events[-1].split_time)

            fd = FrameData(
                frame_idx      = fi,
                timestamp      = ts,
                hip_x_px       = hx,
                hip_y_px       = hy if hy else frame_h / 2,
                hip_x_m        = calibrator.px_to_m(hx),
                hip_x_m_smooth = xm,
                speed_ms       = round(spd, 3),
                accel_ms2      = round(acc, 3),
                body_lean      = lean,
                cone_event     = event_str
            )
        else:
            # No pose this frame — carry last known or zeros
            fd = FrameData(
                frame_idx=fi, timestamp=ts,
                hip_x_px=frame_w//2, hip_y_px=frame_h//2,
                hip_x_m=0, hip_x_m_smooth=0,
                speed_ms=0, accel_ms2=0, body_lean=0,
                cone_event=""
            )

        frame_data_list.append(fd)

        # Annotate frame
        ann = annotator.annotate(
            frame, fd,
            calibrator.cone_a_px, calibrator.cone_b_px,
            frame_w * CONE_ZONE_FRACTION,
            splits, current_cone_label
        )
        annotator.write(ann)

        # Flash event label fades after 0.5s
        if current_cone_label:
            last_ev = detector.events[-1] if detector.events else None
            if last_ev and (ts - last_ev.timestamp) > 0.5:
                current_cone_label = ""

        fi += 1
        if fi % 100 == 0:
            pct = int(fi / max(actual_frame_count, 1) * 100)
            print(f"  ...{pct}% ({fi}/{actual_frame_count} frames)", end="\r")

    annotator.close()
    tracker.close()
    cap.release()
    print()

    # ── Compile results ───────────────────────────────
    events = detector.events
    valid_splits = [s for s in splits if s >= MIN_SPLIT_SECONDS]
    total_shuttles = max(0, len(events) - 1)   # each transition = 1 shuttle leg
    total_time = events[-1].timestamp - events[0].timestamp if len(events) >= 2 else 0.0

    all_speeds = [fd.speed_ms for fd in frame_data_list if fd.speed_ms > 0]
    peak_speed  = float(np.percentile(all_speeds, 98)) if all_speeds else 0.0
    avg_speed   = float(np.mean(all_speeds))           if all_speeds else 0.0

    neg_accels = [abs(fd.accel_ms2) for fd in frame_data_list if fd.accel_ms2 < -0.5]
    avg_decel  = float(np.mean(neg_accels)) if neg_accels else 0.0

    result = AnalysisResult(
        total_shuttles       = total_shuttles,
        total_time_s         = round(total_time, 3),
        splits               = [round(s, 3) for s in valid_splits],
        peak_speed_ms        = round(peak_speed, 2),
        avg_speed_ms         = round(avg_speed, 2),
        peak_accel_ms2       = round(float(np.max([fd.accel_ms2 for fd in frame_data_list if fd.accel_ms2 > 0] or [0])), 2),
        avg_decel_ms2        = round(avg_decel, 2),
        score                = 0.0,
        events               = events,
        frames               = frame_data_list,
        calibration_px_per_m = round(calibrator.px_per_m, 2)
    )
    result.score = compute_scout_score(result)

    # ── Save JSON report ─────────────────────────────
    json_path = os.path.join(output_dir, f"{basename}_report.json")
    report = {
        "video"              : os.path.basename(video_path),
        "cone_distance_ft"   : 30,
        "cone_distance_m"    : CONE_DISTANCE_METERS,
        "calibration_px_per_m": result.calibration_px_per_m,
        "total_shuttle_legs" : result.total_shuttles,
        "total_time_s"       : result.total_time_s,
        "splits_s"           : result.splits,
        "peak_speed_ms"      : result.peak_speed_ms,
        "avg_speed_ms"       : result.avg_speed_ms,
        "peak_accel_ms2"     : result.peak_accel_ms2,
        "avg_decel_ms2"      : result.avg_decel_ms2,
        "scout_score"        : result.score,
        "events"             : [asdict(e) for e in result.events],
    }
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)

    # ── Save CSV ─────────────────────────────────────
    csv_path = os.path.join(output_dir, f"{basename}_frames.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["frame", "timestamp_s", "hip_x_px", "hip_y_px",
                         "hip_x_m_smooth", "speed_ms", "accel_ms2",
                         "body_lean_deg", "cone_event"])
        for fd in frame_data_list:
            writer.writerow([fd.frame_idx, round(fd.timestamp, 4),
                             round(fd.hip_x_px, 1), round(fd.hip_y_px, 1),
                             round(fd.hip_x_m_smooth, 4),
                             fd.speed_ms, fd.accel_ms2,
                             fd.body_lean, fd.cone_event])

    # ── Print summary ────────────────────────────────
    print(f"\n{'='*55}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*55}")
    print(f"  Shuttle legs detected : {result.total_shuttles}")
    print(f"  Total run time        : {result.total_time_s:.3f} s")
    print(f"  Valid splits          : {[f'{s:.3f}s' for s in result.splits]}")
    print(f"  Peak speed            : {result.peak_speed_ms} m/s  "
          f"({result.peak_speed_ms * 3.6:.1f} km/h)")
    print(f"  Avg speed             : {result.avg_speed_ms} m/s")
    print(f"  Avg deceleration      : {result.avg_decel_ms2} m/s²")
    print(f"  Scout Score           : {result.score} / 100")
    print(f"{'='*55}")
    print(f"\n  Outputs saved to: {output_dir}/")
    print(f"    📹 {os.path.basename(out_video_path)}")
    print(f"    📊 {os.path.basename(json_path)}")
    print(f"    📋 {os.path.basename(csv_path)}")
    print()

    return result

# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Shuttle Run Analyzer — 30ft two-cone drill"
    )
    parser.add_argument("video",  help="Path to input video file")
    parser.add_argument("--output", default="output", help="Output directory")
    args = parser.parse_args()

    analyze_video(args.video, args.output)