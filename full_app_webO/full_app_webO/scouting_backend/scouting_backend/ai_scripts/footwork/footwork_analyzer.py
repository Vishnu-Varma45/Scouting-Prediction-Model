"""
footwork_analyzer.py

Single source of truth for badminton footwork analysis.
Same algorithm as the original working script (pose tracking, homography
court calibration, corner/lunge/split-step detection, scoring) — just
wrapped as a callable function that returns structured data instead of
printing to the console.

Public API:
    analyze_footwork(video_path, calibration_points=None, visualize=False)
        -> {"score": ..., "metrics": ..., "sequences": [...]}
"""

import os
os.environ["GLOG_minloglevel"] = "2"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import cv2
import mediapipe as mp
import numpy as np
import math
import json
import urllib.request
from pathlib import Path
from collections import deque
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

# ── MediaPipe (one model, one place it's created) ──────────────────────────────
# Legacy mp.solutions.pose isn't available in this MediaPipe build — use the
# Tasks API instead, same as run_jump() in analysis/runner.py. Reuses the
# pose_landmarker_heavy.task model already downloaded for sprint/jump so it's
# only fetched once across the whole project.
POSE_MODEL_PATH = Path(__file__).resolve().parent.parent / 'sprint' / 'pose_landmarker_heavy.task'
POSE_MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_heavy/float16/latest/"
    "pose_landmarker_heavy.task"
)

# Pose landmark indices (same numbering as mp.solutions.pose.PoseLandmark)
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28


class _LM:
    """Minimal shim so downstream code can keep using lm.x / lm.y like before."""
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x = x
        self.y = y


def _ensure_pose_model():
    POSE_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not POSE_MODEL_PATH.exists():
        urllib.request.urlretrieve(POSE_MODEL_URL, str(POSE_MODEL_PATH))
    return POSE_MODEL_PATH


def _create_pose_detector():
    model_path = _ensure_pose_model()
    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
        # VIDEO mode (not IMAGE) gives cross-frame temporal tracking, which is
        # what smooth_landmarks=True gave us on the old legacy Pose API.
        # IMAGE mode treats every frame independently and is noticeably
        # jitterier — enough to stop the "player is standing still" and
        # "ankle is inside the corner radius" checks from ever firing.
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return vision.PoseLandmarker.create_from_options(options)


# ── Calibration ──────────────────────────────────────────────────────────────
# Resolved relative to this file, not the process's cwd — Django is usually
# launched from the project root, not from ai_scripts/footwork/, so a bare
# relative path here would silently look in the wrong place.
CALIB_FILE = str(Path(__file__).resolve().parent / "court_calibration.json")

# Order corners must be supplied/clicked in: FL, FR, BR, BL
DST_CORNERS = np.float32([[0, 0], [1, 0], [1, 1], [0, 1]])

CORNERS = {
    "FL": (0.0, 0.0),
    "FR": (1.0, 0.0),
    "ML": (0.0, 0.5),
    "MR": (1.0, 0.5),
    "BL": (0.0, 1.0),
    "BR": (1.0, 1.0),
}

CORNER_RADIUS = 0.28  # canonical-space distance to a corner counted as "reached"

# ── Thresholds (single set, used everywhere) ────────────────────────────────────
SPLIT_STEP_MIN_GAP_SEC = 0.35   # min time between two counted split-steps
SPLIT_STEP_WINDOW      = 10     # frames of ankle-Y history to scan
SPLIT_STEP_MIN_AMPL    = 0.020  # min normalized ankle-Y swing to count as real
LUNGE_KNEE_THRESHOLD   = 120    # degrees — below this = deep lunge
SPEED_WINDOW           = 8      # frames to smooth speed calc (canonical space)
STILL_THRESHOLD        = 0.02   # hip movement below this = player stationary
READY_FRAMES_NEEDED    = 6      # consecutive still frames to confirm ready position


# ── Geometry / math helpers ─────────────────────────────────────────────────────
def calc_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba, bc = a - b, c - b
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
    return math.degrees(math.acos(np.clip(cosine, -1.0, 1.0)))


def get_point(lms, idx, w, h):
    lm = lms[idx]
    return (int(lm.x * w), int(lm.y * h))


def dist(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def nearest_corner(hip_x, hip_y):
    best_name, best_dist = None, 999
    for name, (cx, cy) in CORNERS.items():
        d = dist((hip_x, hip_y), (cx, cy))
        if d < best_dist:
            best_dist = d
            best_name = name
    return best_name, best_dist


def to_canonical(H, px, py):
    """Map a pixel coordinate (px, py) into canonical top-down court space via homography H."""
    pt = np.array([[[px, py]]], dtype=np.float32)
    warped = cv2.perspectiveTransform(pt, H)
    return float(warped[0][0][0]), float(warped[0][0][1])


# ── Calibration ──────────────────────────────────────────────────────────────
def calibrate_court(frame, calibration_points=None, visualize=False):
    """
    Resolve the 3x3 homography matrix that maps pixel coords -> canonical
    top-down court coords.

    Priority:
      1. calibration_points passed in explicitly (list of 4 [x, y] pairs,
         order FL, FR, BR, BL) — used as-is, nothing saved/loaded from disk.
      2. CALIB_FILE on disk, if present.
      3. Interactive click-to-calibrate — ONLY when visualize=True (requires
         a display); saves to CALIB_FILE for next time.
      4. Otherwise, raise an explicit error rather than silently hanging
         waiting for a display that isn't there (e.g. headless/Django use).
    """
    if calibration_points is not None:
        pts = calibration_points
        if len(pts) != 4:
            raise ValueError(
                "calibration_points must contain exactly 4 [x, y] points "
                "in order FL, FR, BR, BL."
            )
        return cv2.getPerspectiveTransform(np.float32(pts), DST_CORNERS)

    if os.path.exists(CALIB_FILE):
        with open(CALIB_FILE) as f:
            pts = json.load(f)
        return cv2.getPerspectiveTransform(np.float32(pts), DST_CORNERS)

    if not visualize:
        raise RuntimeError(
            "Footwork analysis requires calibration. Either:\n"
            "1. pass calibration_points,\n"
            "2. place court_calibration.json in the footwork folder,\n"
            "3. or run analyze_footwork(..., visualize=True) once to create it."
        )

    # Interactive fallback (same behavior as the original script) — visualize=True only
    pts = []
    labels = ["FL (front-left)", "FR (front-right)", "BR (back-right, near camera)", "BL (back-left)"]
    clone = frame.copy()
    window_name = "Calibration - click 4 corners IN ORDER, then press any key"

    def on_click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(pts) < 4:
            pts.append([x, y])
            cv2.circle(clone, (x, y), 6, (0, 255, 0), -1)
            cv2.putText(clone, labels[len(pts) - 1], (x + 8, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2, cv2.LINE_AA)

    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, on_click)

    while len(pts) < 4:
        cv2.imshow(window_name, clone)
        if cv2.waitKey(20) & 0xFF == ord('q'):
            break

    cv2.imshow(window_name, clone)
    cv2.waitKey(0)
    cv2.destroyWindow(window_name)

    if len(pts) < 4:
        raise RuntimeError("Calibration cancelled/incomplete.")

    with open(CALIB_FILE, "w") as f:
        json.dump(pts, f)

    return cv2.getPerspectiveTransform(np.float32(pts), DST_CORNERS)


# ── HUD drawing (only used when visualize=True) ─────────────────────────────────
def draw_leg_skeleton(frame, left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle):
    """Draw hip-knee-ankle lines/joints for both legs (replaces mp_drawing.draw_landmarks,
    which isn't available now that mp.solutions is gone)."""
    for a, b in ((left_hip, left_knee), (left_knee, left_ankle),
                 (right_hip, right_knee), (right_knee, right_ankle)):
        cv2.line(frame, a, b, (0, 220, 0), 2)
    for pt in (left_hip, right_hip, left_knee, right_knee, left_ankle, right_ankle):
        cv2.circle(frame, pt, 5, (0, 255, 255), -1)


def draw_panel(frame, metrics):
    panel_w = 330
    panel_h = len(metrics) * 50 + 40
    x0 = frame.shape[1] - panel_w - 10
    y0 = 10
    overlay = frame.copy()
    cv2.rectangle(overlay, (x0 - 8, y0 - 8), (x0 + panel_w, y0 + panel_h), (10, 10, 10), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)
    cv2.rectangle(frame, (x0 - 8, y0 - 8), (x0 + panel_w, y0 + panel_h), (60, 60, 60), 1)
    cv2.putText(frame, "FOOTWORK ANALYSIS", (x0, y0 + 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.50, (180, 180, 180), 1, cv2.LINE_AA)
    cv2.line(frame, (x0 - 8, y0 + 24), (x0 + panel_w, y0 + 24), (60, 60, 60), 1)
    for i, (label, value, color) in enumerate(metrics):
        y = y0 + 42 + i * 50
        cv2.putText(frame, label, (x0, y - 14),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.36, (130, 130, 130), 1, cv2.LINE_AA)
        cv2.putText(frame, value, (x0, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.68, color, 2, cv2.LINE_AA)
        if i < len(metrics) - 1:
            cv2.line(frame, (x0 - 8, y + 10), (x0 + panel_w, y + 10), (35, 35, 35), 1)


def draw_status_badge(frame, text, color):
    label = f"  {text}  "
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
    cv2.rectangle(frame, (8, 8), (18 + tw, 20 + th), color, -1)
    cv2.putText(frame, label, (10, 12 + th),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2, cv2.LINE_AA)


def draw_court_map(frame, hip_x, hip_y, visited, current_corner):
    mx, my = 10, frame.shape[0] - 160
    mw, mh = 180, 140
    overlay = frame.copy()
    cv2.rectangle(overlay, (mx, my), (mx + mw, my + mh), (10, 10, 10), -1)
    cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)
    cv2.rectangle(frame, (mx, my), (mx + mw, my + mh), (60, 60, 60), 1)
    cv2.putText(frame, "COURT MAP (calibrated)", (mx + 4, my + 14),
                cv2.FONT_HERSHEY_SIMPLEX, 0.32, (150, 150, 150), 1, cv2.LINE_AA)

    for name, (cx, cy) in CORNERS.items():
        px = int(mx + cx * mw)
        py = int(my + 20 + cy * (mh - 24))
        if name in visited:
            col = (0, 200, 80)
            cv2.circle(frame, (px, py), 10, col, -1)
        else:
            col = (80, 80, 80)
            cv2.circle(frame, (px, py), 10, col, 1)
        cv2.putText(frame, name, (px - 10, py + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.30, (220, 220, 220), 1, cv2.LINE_AA)

    hx = max(0.0, min(1.0, hip_x))
    hy = max(0.0, min(1.0, hip_y))
    px = int(mx + hx * mw)
    py = int(my + 20 + hy * (mh - 24))
    cv2.circle(frame, (px, py), 6, (0, 180, 255), -1)


# ── Scoring (single implementation, shared by every sequence) ──────────────────
def _score_sequence(seq):
    """Turn one completed sequence's raw tracking data into scored metrics."""
    ct = seq["completion_time"]

    if ct < 5.0:
        time_sc, time_band = 100, "Elite — very fast sequence"
    elif ct < 7.0:
        time_sc, time_band = 80, "Strong — above threshold"
    elif ct < 9.0:
        time_sc, time_band = 60, "Threshold — acceptable"
    else:
        time_sc, time_band = max(0, int(100 - (ct - 5) * 10)), "Below threshold — needs work"

    all_speeds = list(seq["corner_speeds"].values())
    if len(all_speeds) > 1:
        speed_cv = np.std(all_speeds) / (np.mean(all_speeds) + 1e-6)
        tech_sc = max(0, int(100 - speed_cv * 200))
    else:
        tech_sc = 60 if all_speeds else 50

    lunge_angles = seq["lunge_angles"]
    if lunge_angles:
        min_lunge = min(lunge_angles)
        avg_lunge = float(np.mean(lunge_angles))
        if min_lunge < 90:
            lunge_sc, lunge_band = 100, "Excellent — deep lunge, full court coverage"
        elif min_lunge < 105:
            lunge_sc, lunge_band = 80, "Good — adequate lunge depth"
        elif min_lunge < 120:
            lunge_sc, lunge_band = 60, "Moderate — could go deeper"
        else:
            lunge_sc, lunge_band = 30, "Shallow — not reaching full court"
    else:
        min_lunge, avg_lunge = None, None
        lunge_sc, lunge_band = 20, f"No deep lunges detected (threshold: < {LUNGE_KNEE_THRESHOLD} deg)"

    ss = seq["split_steps"]
    ss_sc = min(100, ss * 20)
    if ss >= 5:
        ss_band = "Excellent — consistent split-step habit"
    elif ss >= 3:
        ss_band = "Good — split-step present"
    elif ss >= 1:
        ss_band = "Inconsistent — needs more split-step training"
    else:
        ss_band = "None detected — no split-step habit"

    ls, rs = seq["left_speeds"], seq["right_speeds"]
    if ls and rs:
        avg_ls, avg_rs = float(np.mean(ls) * 100), float(np.mean(rs) * 100)
        sym_speed = min(avg_ls, avg_rs) / max(avg_ls, avg_rs) * 100 if max(avg_ls, avg_rs) > 0 else 0
        eff_sc = int(sym_speed)
        if sym_speed >= 90:
            sym_band = "Excellent bilateral symmetry"
        elif sym_speed >= 75:
            sym_band = "Good — minor imbalance"
        else:
            sym_band = "Significant asymmetry — strengthen weaker side"
    else:
        avg_ls, avg_rs, sym_speed = None, None, None
        eff_sc = 50
        sym_band = "Not enough data for symmetry calculation"

    final_score = int(
        time_sc * 0.30 + tech_sc * 0.25 + lunge_sc * 0.15 + ss_sc * 0.15 + eff_sc * 0.15
    )

    if final_score >= 85:
        band = "ELITE"
    elif final_score >= 70:
        band = "STRONG — shortlist candidate"
    elif final_score >= 55:
        band = "THRESHOLD — borderline"
    else:
        band = "BELOW THRESHOLD"

    return {
        "completion_time": ct,
        "completion_time_assessment": time_band,
        "corner_times": seq["corner_times"],
        "corner_speeds": seq["corner_speeds"],
        "lunge": {
            "deepest_angle_deg": min_lunge,
            "average_angle_deg": avg_lunge,
            "assessment": lunge_band,
        },
        "split_steps": {
            "count": ss,
            "assessment": ss_band,
        },
        "symmetry": {
            "avg_speed_left": avg_ls,
            "avg_speed_right": avg_rs,
            "symmetry_pct": sym_speed,
            "assessment": sym_band,
        },
        "score_breakdown": {
            "completion_time_pts": time_sc,
            "footwork_tech_pts": tech_sc,
            "lunge_depth_pts": lunge_sc,
            "split_step_pts": ss_sc,
            "movement_efficiency_pts": eff_sc,
        },
        "score": final_score,
        "band": band,
    }


# ── Main entry point ─────────────────────────────────────────────────────────
def analyze_footwork(video_path, calibration_points=None, visualize=False):
    """
    Run the full footwork analysis pipeline on a video.

    Args:
        video_path: path to the input video file.
        calibration_points: optional list of 4 [x, y] pixel points on the
            first frame, in order FL, FR, BR, BL. If omitted, falls back to
            court_calibration.json on disk, then to interactive click
            calibration (requires a display).
        visualize: if True, shows a live annotated window while processing
            (same HUD as the original script). Off by default.

    Returns:
        {
            "score": int | None,              # score of the best sequence
            "metrics": {...} | None,           # full metrics for the best sequence
            "sequences": [ {...}, ... ]        # metrics for every completed sequence
        }
    """
    detector = _create_pose_detector()

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        detector.close()
        raise IOError(f"Could not open video: {video_path}")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        ret, first_frame = cap.read()
        if not ret:
            raise IOError("Could not read first frame for calibration.")
        H_court = calibrate_court(first_frame, calibration_points=calibration_points, visualize=visualize)
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        # Derived (frame-based) thresholds
        split_step_min_gap = int(fps * SPLIT_STEP_MIN_GAP_SEC)

        # ── Tracking state ──────────────────────────────────────────────────
        frame_index = 0
        last_timestamp_ms = -1
        sequence_start = None
        sequence_active = False

        corners_visited = set()
        corner_times = {}
        corner_speeds = {}

        hip_history = deque(maxlen=SPEED_WINDOW)
        speed_history = []
        left_speeds = []
        right_speeds = []

        lunge_angles = []

        ankle_y_history = deque(maxlen=SPLIT_STEP_WINDOW)
        split_steps_detected = 0
        last_split_frame = -split_step_min_gap

        left_corner_times = []
        right_corner_times = []

        # ── Diagnostics (only used to explain a failed/empty result) ────────
        diag_frames_with_pose = 0
        diag_ever_ready = False
        diag_max_corners_seen = 0
        diag_sequences_attempted = 0
        diag_min_dist_per_corner = {name: None for name in CORNERS}

        still_frame_count = 0
        last_hip_pos = None

        sequences = []

        live = {
            "corner": "—", "speed": 0.0, "lunge_angle": 0.0,
            "split_steps": 0, "elapsed": 0.0, "corners_done": 0,
        }
        status_text, status_color = "WAITING", (120, 120, 120)

        window_name = "Badminton Footwork Analysis"
        if visualize:
            cv2.namedWindow(window_name)

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            timestamp_ms = int(frame_index * (1000.0 / fps))
            if timestamp_ms <= last_timestamp_ms:
                timestamp_ms = last_timestamp_ms + 1
            last_timestamp_ms = timestamp_ms
            detection = detector.detect_for_video(mp_image, timestamp_ms)

            hip_x, hip_y = 0.5, 0.5

            if detection.pose_landmarks and len(detection.pose_landmarks) > 0:
                diag_frames_with_pose += 1
                raw = detection.pose_landmarks[0]
                lms = [_LM(lm.x, lm.y) for lm in raw]

                LEFT_HIP = get_point(lms, L_HIP, w, h)
                RIGHT_HIP = get_point(lms, R_HIP, w, h)
                LEFT_KNEE = get_point(lms, L_KNEE, w, h)
                RIGHT_KNEE = get_point(lms, R_KNEE, w, h)
                LEFT_ANKLE = get_point(lms, L_ANKLE, w, h)
                RIGHT_ANKLE = get_point(lms, R_ANKLE, w, h)

                # Ankle midpoint (not hip) for court position — avoids parallax
                # error from warping a point that isn't on the floor plane.
                ankle_px = ((LEFT_ANKLE[0] + RIGHT_ANKLE[0]) / 2, (LEFT_ANKLE[1] + RIGHT_ANKLE[1]) / 2)
                hip_x, hip_y = to_canonical(H_court, ankle_px[0], ankle_px[1])

                la_y = lms[L_ANKLE].y
                ra_y = lms[R_ANKLE].y

                left_knee_angle = calc_angle(LEFT_HIP, LEFT_KNEE, LEFT_ANKLE)
                right_knee_angle = calc_angle(RIGHT_HIP, RIGHT_KNEE, RIGHT_ANKLE)
                min_knee = min(left_knee_angle, right_knee_angle)

                hip_history.append((hip_x, hip_y, frame_index))
                speed = 0.0
                if len(hip_history) >= 2:
                    dx = hip_history[-1][0] - hip_history[0][0]
                    dy = hip_history[-1][1] - hip_history[0][1]
                    dt = (hip_history[-1][2] - hip_history[0][2]) / fps
                    if dt > 0:
                        speed = math.sqrt(dx ** 2 + dy ** 2) / dt
                live["speed"] = speed

                if last_hip_pos is not None:
                    movement = dist((hip_x, hip_y), last_hip_pos)
                    still_frame_count = still_frame_count + 1 if movement < STILL_THRESHOLD else 0
                last_hip_pos = (hip_x, hip_y)

                player_ready = still_frame_count >= READY_FRAMES_NEEDED

                if player_ready and not sequence_active:
                    sequence_active = True
                    sequence_start = frame_index
                    corners_visited = set()
                    corner_times = {}
                    corner_speeds = {}
                    status_text, status_color = "SEQUENCE ACTIVE", (0, 200, 80)
                    diag_ever_ready = True
                    diag_sequences_attempted += 1

                if sequence_active:
                    elapsed = (frame_index - sequence_start) / fps
                    live["elapsed"] = elapsed

                    corner_name, corner_dist = nearest_corner(hip_x, hip_y)

                    # Track closest-ever approach to EVERY corner (not just the
                    # nearest one) so a near-miss can be told apart from the
                    # player never getting close at all.
                    for cname, (cx, cy) in CORNERS.items():
                        d = dist((hip_x, hip_y), (cx, cy))
                        if diag_min_dist_per_corner[cname] is None or d < diag_min_dist_per_corner[cname]:
                            diag_min_dist_per_corner[cname] = d

                    if corner_dist < CORNER_RADIUS and corner_name not in corners_visited:
                        corners_visited.add(corner_name)
                        corner_times[corner_name] = elapsed
                        corner_speeds[corner_name] = speed

                        if corner_name in ("FL", "ML", "BL"):
                            left_corner_times.append(elapsed)
                            left_speeds.append(speed)
                        else:
                            right_corner_times.append(elapsed)
                            right_speeds.append(speed)

                        speed_history.append(speed)
                        live["corners_done"] = len(corners_visited)
                        live["corner"] = corner_name
                        diag_max_corners_seen = max(diag_max_corners_seen, len(corners_visited))

                        if min_knee < LUNGE_KNEE_THRESHOLD:
                            lunge_angles.append(min_knee)

                    if len(corners_visited) == 6:
                        completion_time = elapsed
                        sequences.append(_score_sequence({
                            "completion_time": completion_time,
                            "corner_times": corner_times.copy(),
                            "corner_speeds": corner_speeds.copy(),
                            "lunge_angles": lunge_angles.copy(),
                            "split_steps": split_steps_detected,
                            "left_times": left_corner_times.copy(),
                            "right_times": right_corner_times.copy(),
                            "left_speeds": left_speeds.copy(),
                            "right_speeds": right_speeds.copy(),
                        }))
                        sequence_active = False
                        status_text, status_color = "SEQUENCE DONE", (0, 215, 255)
                        corners_visited = set()
                        left_corner_times, right_corner_times = [], []
                        left_speeds, right_speeds = [], []
                        lunge_angles = []
                        split_steps_detected = 0

                # ── Split-step detection (peak-based, debounced) ────────────
                ankle_y_history.append((la_y + ra_y) / 2)
                if len(ankle_y_history) == SPLIT_STEP_WINDOW:
                    vals = list(ankle_y_history)
                    mid_idx = SPLIT_STEP_WINDOW // 2
                    mid_val = min(vals[mid_idx - 1: mid_idx + 2])
                    dip_from_start = vals[0] - mid_val
                    rise_to_end = vals[-1] - mid_val
                    is_dip_then_rise = dip_from_start > SPLIT_STEP_MIN_AMPL and rise_to_end > SPLIT_STEP_MIN_AMPL

                    if is_dip_then_rise and (frame_index - last_split_frame) >= split_step_min_gap:
                        split_steps_detected += 1
                        last_split_frame = frame_index
                        live["split_steps"] = split_steps_detected

                if min_knee < LUNGE_KNEE_THRESHOLD:
                    live["lunge_angle"] = min_knee

                if visualize:
                    draw_leg_skeleton(frame, LEFT_HIP, RIGHT_HIP, LEFT_KNEE, RIGHT_KNEE, LEFT_ANKLE, RIGHT_ANKLE)

            if visualize:
                draw_court_map(frame, hip_x, hip_y, corners_visited, live["corner"])
                elapsed_str = f"{live['elapsed']:.2f} s"
                speed_str = f"{live['speed']*100:.1f} u/s"
                lunge_str = f"{live['lunge_angle']:.1f} deg" if live['lunge_angle'] > 0 else "-- deg"
                split_str = f"{live['split_steps']}"
                corners_str = f"{live['corners_done']} / 6  [{live['corner']}]"
                metrics_panel = [
                    ("COMPLETION TIME", elapsed_str, (0, 215, 255) if live['elapsed'] < 8 else (0, 140, 255)),
                    ("SPEED TO CORNER", speed_str, (80, 200, 80) if live['speed'] > 0.05 else (0, 165, 255)),
                    ("LUNGE DEPTH (knee angle)", lunge_str, (80, 200, 80) if 0 < live['lunge_angle'] < 105 else (0, 165, 255)),
                    ("SPLIT STEPS", split_str, (80, 200, 80) if live['split_steps'] > 0 else (140, 140, 140)),
                    ("CORNERS REACHED", corners_str, (80, 200, 80) if live['corners_done'] == 6 else (0, 165, 255)),
                ]
                draw_panel(frame, metrics_panel)
                draw_status_badge(frame, status_text, status_color)
                cv2.imshow(window_name, frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            frame_index += 1

    finally:
        cap.release()
        if visualize:
            cv2.destroyAllWindows()
        detector.close()

    if not sequences:
        diagnostics = {
            "total_frames_processed": frame_index,
            "frames_with_pose_detected": diag_frames_with_pose,
            "player_ever_reached_ready_position": diag_ever_ready,
            "sequences_attempted": diag_sequences_attempted,
            "max_corners_reached_in_one_attempt": diag_max_corners_seen,
            "corners_reached_in_last_attempt": sorted(corners_visited),
            "corners_never_reached": sorted(set(CORNERS.keys()) - corners_visited),
            "closest_approach_per_corner": {
                name: (round(d, 3) if d is not None else None)
                for name, d in diag_min_dist_per_corner.items()
            },
            "corner_radius_threshold": CORNER_RADIUS,
        }

        # Graceful degradation: if the player reached most (but not all 6)
        # corners, score the partial attempt instead of hard-failing outright.
        # This is clearly flagged as partial — it is NOT the same as a real
        # 6/6 completion, but it keeps the app usable while a corner (e.g.
        # one near the camera) is hard to calibrate perfectly.
        MIN_CORNERS_FOR_PARTIAL_SCORE = 3
        if len(corners_visited) >= MIN_CORNERS_FOR_PARTIAL_SCORE:
            partial_elapsed = live["elapsed"] if sequence_active else 0.0
            partial = _score_sequence({
                "completion_time": partial_elapsed,
                "corner_times": corner_times.copy(),
                "corner_speeds": corner_speeds.copy(),
                "lunge_angles": lunge_angles.copy(),
                "split_steps": split_steps_detected,
                "left_times": left_corner_times.copy(),
                "right_times": right_corner_times.copy(),
                "left_speeds": left_speeds.copy(),
                "right_speeds": right_speeds.copy(),
            })
            partial["is_partial"] = True
            partial["corners_reached"] = sorted(corners_visited)
            partial["corners_missed"] = sorted(set(CORNERS.keys()) - corners_visited)
            # A partial attempt didn't earn its full completion-time credit —
            # scale the score down in proportion to corners actually reached
            # so it can't outscore a genuine 6/6 run.
            partial["score"] = int(partial["score"] * len(corners_visited) / 6)

            return {
                "score": partial["score"],
                "metrics": partial,
                "sequences": [partial],
                "diagnostics": diagnostics,
            }

        return {"score": None, "metrics": None, "sequences": [], "diagnostics": diagnostics}

    best = max(sequences, key=lambda s: s["score"])
    return {"score": best["score"], "metrics": best, "sequences": sequences}


# ── Optional: run directly for interactive HUD debugging ───────────────────────
if __name__ == "__main__":
    import sys
    import json

    video = sys.argv[1] if len(sys.argv) > 1 else "video.mp4"
    result = analyze_footwork(video, visualize=True)
    print(json.dumps(result, indent=2))