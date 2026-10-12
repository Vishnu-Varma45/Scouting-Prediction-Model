import cv2
import numpy as np
from scipy.signal import find_peaks, savgol_filter
from metrics import calculate_angle
from pose import get_pose_detector, get_pose_module

# ──────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────

SPRINT_DISTANCE_METERS = 20

# Minimum landmark visibility to trust a reading
VISIBILITY_THRESHOLD = 0.45

# Landmarks required to be visible every frame
REQUIRED_LANDMARKS = {
    11: "left_shoulder",
    12: "right_shoulder",
    23: "left_hip",
    24: "right_hip",
    25: "left_knee",
    26: "right_knee",
    27: "left_ankle",
    28: "right_ankle",
}

# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def remove_outliers(data: list, z_thresh: float = 2.0) -> list:
    """Remove values more than z_thresh standard deviations from the median."""
    if len(data) < 5:
        return data
    arr = np.array(data, dtype=float)
    median = np.median(arr)
    std = np.std(arr)
    if std == 0:
        return data
    return [x for x in data if abs(x - median) < z_thresh * std]


def smooth_signal(data: list, window: int = 7) -> np.ndarray:
    """
    Apply Savitzky-Golay smoothing to reduce per-frame noise.
    Falls back to raw array when there are too few points.
    """
    arr = np.array(data, dtype=float)
    if len(arr) < window + 2:
        return arr
    # window must be odd
    w = window if window % 2 == 1 else window + 1
    return savgol_filter(arr, window_length=w, polyorder=2)


def compute_trunk_angle_lateral(shoulder_mid: list, hip_mid: list) -> float:
    """
    For a SIDE-VIEW (lateral) camera the athlete moves left→right or right→left.
    We measure trunk lean as the deviation from vertical:
      - 0°  = perfectly upright
      - +ve = leaning forward (desired during acceleration)
    Uses normalised MediaPipe coords where y increases downward.
    """
    dx = shoulder_mid[0] - hip_mid[0]   # horizontal offset
    dy = hip_mid[1] - shoulder_mid[1]   # vertical offset (positive = shoulder above hip ✓)

    # Angle of trunk vector relative to the upward vertical
    angle_rad = np.arctan2(abs(dx), max(abs(dy), 1e-6))
    return float(np.degrees(angle_rad))


def landmarks_visible(landmarks, ids: dict, threshold: float) -> bool:
    """Return True only if every required landmark meets the visibility threshold."""
    return all(landmarks[i].visibility >= threshold for i in ids)


def count_steps_from_knee_drive(
    left_knee_angles: list,
    right_knee_angles: list,
    fps: float,
) -> int:
    """
    Count steps from alternating knee-drive peaks on BOTH legs (side view).
    Each peak = one knee reaching maximum flexion = one step.
    More reliable than ankle separation for a lateral camera.
    """
    min_distance = max(3, int(fps * 0.12))   # ~120 ms between steps minimum

    left_arr  = smooth_signal(left_knee_angles)
    right_arr = smooth_signal(right_knee_angles)

    # Invert because flexion = lower angle value; peaks on inverted = troughs on original
    left_peaks,  _ = find_peaks(-left_arr,  distance=min_distance, prominence=8)
    right_peaks, _ = find_peaks(-right_arr, distance=min_distance, prominence=8)

    return len(left_peaks) + len(right_peaks)


# ──────────────────────────────────────────────
# MAIN ANALYSIS
# ──────────────────────────────────────────────

def analyze_video(video_path: str) -> dict:

    pose    = get_pose_detector()
    mp_pose = get_pose_module()

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": f"Could not open video: {video_path}"}

    fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width  = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    # ── Camera validation ──────────────────────
    camera_validation = []
    if fps < 50:
        camera_validation.append(f"FPS is {fps:.1f} — recommend ≥60 fps for sprint analysis")
    if width < 1920:
        camera_validation.append(f"Resolution {int(width)}×{int(height)} — recommend 1080p or higher")
    if width < height:
        camera_validation.append("Video appears to be in portrait mode — use landscape for sprint capture")

    # ── Per-frame accumulators ─────────────────
    left_knee_angles  = []
    right_knee_angles = []
    trunk_angles      = []
    ankle_separations = []

    frame_count      = 0
    valid_frames     = 0
    lost_pose_frames = 0
    low_vis_frames   = 0

    # ── Frame loop ─────────────────────────────
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame_count += 1
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)

        # No pose detected at all
        if not results.pose_landmarks:
            lost_pose_frames += 1
            continue

        lm = results.pose_landmarks.landmark

        # Skip frames where key landmarks are not sufficiently visible
        if not landmarks_visible(lm, REQUIRED_LANDMARKS, VISIBILITY_THRESHOLD):
            low_vis_frames += 1
            continue

        valid_frames += 1

        # ── Extract landmarks ──────────────────
        left_shoulder  = lm[11]
        right_shoulder = lm[12]
        left_hip       = lm[23]
        right_hip      = lm[24]
        left_knee      = lm[25]
        right_knee     = lm[26]
        left_ankle     = lm[27]
        right_ankle    = lm[28]

        # ── Knee angles ────────────────────────
        left_knee_angle = calculate_angle(
            [left_hip.x,   left_hip.y],
            [left_knee.x,  left_knee.y],
            [left_ankle.x, left_ankle.y],
        )
        right_knee_angle = calculate_angle(
            [right_hip.x,   right_hip.y],
            [right_knee.x,  right_knee.y],
            [right_ankle.x, right_ankle.y],
        )

        # Plausibility gate: MediaPipe side-view angles should be 30°–180°
        if 30 <= left_knee_angle  <= 180:
            left_knee_angles.append(left_knee_angle)
        if 30 <= right_knee_angle <= 180:
            right_knee_angles.append(right_knee_angle)

        # ── Trunk angle (lateral camera) ───────
        shoulder_mid = [
            (left_shoulder.x + right_shoulder.x) / 2,
            (left_shoulder.y + right_shoulder.y) / 2,
        ]
        hip_mid = [
            (left_hip.x + right_hip.x) / 2,
            (left_hip.y + right_hip.y) / 2,
        ]
        trunk_angle = compute_trunk_angle_lateral(shoulder_mid, hip_mid)
        trunk_angles.append(trunk_angle)

        # ── Ankle separation ───────────────────
        ankle_sep = abs(left_ankle.x - right_ankle.x)
        ankle_separations.append(ankle_sep)

    cap.release()

    # ── Guard: nothing useful captured ────────
    if valid_frames == 0 or len(left_knee_angles) == 0:
        return {
            "error": "No valid pose data captured. "
                     "Check lighting, camera angle, and that the full body is in frame.",
            "frames": frame_count,
            "lost_pose_frames": lost_pose_frames,
            "low_visibility_frames": low_vis_frames,
        }

    # ── Diagnostics ───────────────────────────
    print(f"Total frames   : {frame_count}")
    print(f"Valid frames   : {valid_frames}")
    print(f"Lost pose      : {lost_pose_frames}")
    print(f"Low visibility : {low_vis_frames}")
    print(f"Left knee pts  : {len(left_knee_angles)}")
    print(f"Right knee pts : {len(right_knee_angles)}")
    print(f"Trunk pts      : {len(trunk_angles)}")

    # ── Smooth & clean signals ─────────────────
    left_knee_clean  = remove_outliers(left_knee_angles)
    right_knee_clean = remove_outliers(right_knee_angles)
    trunk_clean      = remove_outliers(trunk_angles)

    # ── Step count (knee-drive method) ─────────
    step_count = count_steps_from_knee_drive(left_knee_angles, right_knee_angles, fps)

    # ── Time / speed ───────────────────────────
    # Use valid_frames (frames with good pose) rather than total frame_count
    # to avoid inflating duration with frames where the athlete is off-screen.
    video_duration = frame_count / fps if fps > 0 else 0
    active_duration = valid_frames / fps if fps > 0 else 0

    step_frequency = step_count / active_duration if active_duration > 0 else 0

    # Speed: only meaningful if this video actually covers the full sprint distance.
    # Use video_duration (wall-clock) not active_duration for speed.
    avg_speed = (SPRINT_DISTANCE_METERS / video_duration) if video_duration > 0 else 0

    # ── Aggregate metrics ──────────────────────
    mean_left_knee  = float(np.mean(left_knee_clean))
    mean_right_knee = float(np.mean(right_knee_clean))
    mean_trunk      = float(np.mean(trunk_clean))
    trunk_std       = float(np.std(trunk_clean))

    mean_ankle_sep  = float(np.mean(ankle_separations))
    max_ankle_sep   = float(np.max(ankle_separations))
    min_ankle_sep   = float(np.min(ankle_separations))

    # ── Asymmetry index (0 = perfect symmetry) ─
    knee_asymmetry = abs(mean_left_knee - mean_right_knee)

    # ── Confidence score ───────────────────────
    # Start at 100, deduct for data quality issues
    confidence_score = 100.0

    bad_frame_ratio = (lost_pose_frames + low_vis_frames) / max(frame_count, 1)
    confidence_score -= min(35, bad_frame_ratio * 100)   # up to -35 for poor visibility

    if trunk_std > 15:
        confidence_score -= 10    # very erratic trunk readings

    if len(left_knee_angles) < 10 or len(right_knee_angles) < 10:
        confidence_score -= 20    # too few samples

    if knee_asymmetry > 25:
        confidence_score -= 5     # suspicious left/right divergence

    confidence_score = max(0.0, confidence_score)

    if confidence_score >= 80:
        confidence = "HIGH"
    elif confidence_score >= 55:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # ── Flags ──────────────────────────────────
    flags = []

    if mean_trunk > 45:
        flags.append(
            f"Excessive trunk lean ({mean_trunk:.1f}°) — check if athlete is bending at waist"
        )
    if mean_trunk < 5:
        flags.append(
            f"Trunk appears nearly vertical ({mean_trunk:.1f}°) — expected forward lean during sprint"
        )
    if step_frequency > 6.5:
        flags.append(
            f"Step frequency ({step_frequency:.2f} steps/s) is unrealistically high — verify video fps"
        )
    if step_frequency < 2.0 and active_duration > 2:
        flags.append(
            f"Step frequency ({step_frequency:.2f} steps/s) is very low — check step detection"
        )
    if mean_left_knee < 40:
        flags.append(
            f"Left knee mean angle ({mean_left_knee:.1f}°) is very low — possible detection error"
        )
    if mean_right_knee < 40:
        flags.append(
            f"Right knee mean angle ({mean_right_knee:.1f}°) is very low — possible detection error"
        )
    if knee_asymmetry > 20:
        flags.append(
            f"Large left/right knee angle asymmetry ({knee_asymmetry:.1f}°) — potential injury risk"
        )
    if bad_frame_ratio > 0.3:
        flags.append(
            f"{bad_frame_ratio*100:.0f}% of frames had poor or missing pose — results may be unreliable"
        )

    # ── Grading ────────────────────────────────
    # Elite sprinters: ~4.5–5.5 steps/s at top speed (stride = 2 steps)
    if step_frequency >= 4.5:
        stride_grade = "ELITE"
    elif step_frequency >= 3.8:
        stride_grade = "PASS"
    else:
        stride_grade = "FAIL"

    # ── Athlete score ──────────────────────────
    athlete_score = 60  # base

    # Step rate
    if step_frequency >= 4.5:
        athlete_score += 15
    elif step_frequency >= 3.8:
        athlete_score += 8

    # Trunk control
    if trunk_std < 8:
        athlete_score += 10
    elif trunk_std < 14:
        athlete_score += 5

    # Knee drive range (peak flexion during drive phase expected ~60–100°)
    min_left  = float(np.min(left_knee_angles))
    min_right = float(np.min(right_knee_angles))
    if min_left <= 90 and min_right <= 90:
        athlete_score += 10   # good knee drive on both sides

    # Symmetry
    if knee_asymmetry < 10:
        athlete_score += 5

    # Confidence quality bonus
    if confidence_score >= 80:
        athlete_score += 5

    athlete_score = min(int(athlete_score), 100)

    # ── Report ─────────────────────────────────
    report = {
        # Frame / time
        "frames":               frame_count,
        "valid_frames":         valid_frames,
        "lost_pose_frames":     lost_pose_frames,
        "low_visibility_frames": low_vis_frames,
        "video_duration_s":     round(video_duration, 2),
        "active_duration_s":    round(active_duration, 2),

        # Knee angles
        "mean_left_knee":       round(mean_left_knee,  2),
        "mean_right_knee":      round(mean_right_knee, 2),
        "max_left_knee":        round(float(np.max(left_knee_clean)),  2),
        "min_left_knee":        round(float(np.min(left_knee_clean)),  2),
        "max_right_knee":       round(float(np.max(right_knee_clean)), 2),
        "min_right_knee":       round(float(np.min(right_knee_clean)), 2),
        "knee_asymmetry_deg":   round(knee_asymmetry, 2),

        # Trunk
        "mean_trunk_angle":     round(mean_trunk, 2),
        "trunk_consistency_std": round(trunk_std,  2),

        # Ankle / stride
        "mean_ankle_separation": round(mean_ankle_sep, 4),
        "max_ankle_separation":  round(max_ankle_sep,  4),
        "min_ankle_separation":  round(min_ankle_sep,  4),

        # Stride
        "step_count":           step_count,
        "step_frequency":       round(step_frequency, 2),
        "stride_grade":         stride_grade,

        # Speed
        "average_speed_ms":     round(avg_speed, 2),

        # Quality
        "confidence":           confidence,
        "confidence_score":     round(confidence_score, 2),
        "athlete_score":        athlete_score,

        # Issues
        "flags":                flags,
        "camera_validation":    camera_validation,
    }

    return report