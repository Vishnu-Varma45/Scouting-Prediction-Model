"""
analysis/runner.py
──────────────────
Central dispatcher that calls the correct AI script for each test type
and returns a standardised metrics dict + score.

Each run_* function:
  - Accepts a video file path (string)
  - Returns a dict with two keys:
      {
        "metrics": { ...all AI-extracted values... },
        "score":   float (0-100)
      }
  - On error returns:
      { "error": "description", "metrics": {}, "score": 0 }
"""

import os
import cv2
import mediapipe as mp
import sys
import math
import traceback
import numpy as np
from collections import deque
from pathlib import Path
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
import urllib.request

# ── Score helpers ──────────────────────────────────────────────────────────────

def clamp(value, low=0, high=100):
    return max(low, min(high, value))


# ══════════════════════════════════════════════════════════════════════════════
# TEST 1 — 0-10m Sprint
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# PASTE THIS INTO analysis/runner.py
# Replace run_sprint() and run_jump() entirely with these two functions
# ══════════════════════════════════════════════════════════════════════════════

def run_sprint(video_path: str) -> dict:
    sprint_dir = Path(__file__).resolve().parent.parent / 'ai_scripts' / 'sprint'
    try:
        sys.path.insert(0, str(sprint_dir))
        from analyzer import analyze_video

        result = analyze_video(str(video_path))

        if 'error' in result:
            return {"error": result['error'], "metrics": {}, "score": 0}

        metrics = {
            # Frame stats
            "frames"                 : result.get("frames"),
            "valid_frames"           : result.get("valid_frames"),
            "lost_pose_frames"       : result.get("lost_pose_frames"),
            "low_visibility_frames"  : result.get("low_visibility_frames"),
            # Timing
            "video_duration_s"       : result.get("video_duration_s"),
            "active_duration_s"      : result.get("active_duration_s"),
            # Knee angles
            "mean_left_knee"         : result.get("mean_left_knee"),
            "mean_right_knee"        : result.get("mean_right_knee"),
            "max_left_knee"          : result.get("max_left_knee"),
            "min_left_knee"          : result.get("min_left_knee"),
            "max_right_knee"         : result.get("max_right_knee"),
            "min_right_knee"         : result.get("min_right_knee"),
            "knee_asymmetry_deg"     : result.get("knee_asymmetry_deg"),
            # Trunk
            "mean_trunk_angle"       : result.get("mean_trunk_angle"),
            "trunk_consistency_std"  : result.get("trunk_consistency_std"),
            # Stride
            "mean_ankle_separation"  : result.get("mean_ankle_separation"),
            "max_ankle_separation"   : result.get("max_ankle_separation"),
            "min_ankle_separation"   : result.get("min_ankle_separation"),
            "step_count"             : result.get("step_count"),
            "step_frequency"         : result.get("step_frequency"),
            "stride_grade"           : result.get("stride_grade"),
            # Speed & confidence
            "average_speed_ms"       : result.get("average_speed_ms"),
            "confidence"             : result.get("confidence"),
            "confidence_score"       : result.get("confidence_score"),
            # Flags & validation
            "flags"                  : result.get("flags", []),
            "camera_validation"      : result.get("camera_validation", []),
        }
        score = clamp(result.get("athlete_score", 0))
        return {"metrics": metrics, "score": score}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "metrics": {}, "score": 0}
    finally:
        if str(sprint_dir) in sys.path:
            sys.path.remove(str(sprint_dir))


def run_jump(video_path: str) -> dict:
    """
    Vertical jump analysis using new mediapipe tasks API.
    Reuses the pose_landmarker_heavy.task model already downloaded by sprint.
    """
    try:
        import cv2
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        # Reuse model downloaded by sprint
        model_path = (
            Path(__file__).resolve().parent.parent
            / 'ai_scripts' / 'sprint' / 'pose_landmarker_heavy.task'
        )

        # Download if not present (first run before sprint)
        if not model_path.exists():
            import urllib.request
            print("Downloading pose model for jump analysis...")
            urllib.request.urlretrieve(
                "https://storage.googleapis.com/mediapipe-models/"
                "pose_landmarker/pose_landmarker_heavy/float16/latest/"
                "pose_landmarker_heavy.task",
                str(model_path)
            )

        options = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(
                model_asset_path=str(model_path)
            ),
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        detector = vision.PoseLandmarker.create_from_options(options)

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return {"error": "Could not open video", "metrics": {}, "score": 0}

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

        # Landmark shim — mimics old .x .y interface
        class _LM:
            def __init__(self, x, y):
                self.x = x
                self.y = y

        def get_pt(lms, idx, w, h):
            lm = lms[idx]
            return (int(lm.x * w), int(lm.y * h))

        def get_y(lms, idx):
            return lms[idx].y

        def calc_angle(a, b, c):
            a, b, c = np.array(a), np.array(b), np.array(c)
            ba, bc  = a - b, c - b
            cosine  = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
            return math.degrees(math.acos(np.clip(cosine, -1.0, 1.0)))

        # Landmark indices
        L_HIP    = 23; R_HIP    = 24
        L_KNEE   = 25; R_KNEE   = 26
        L_ANKLE  = 27; R_ANKLE  = 28

        JUMP_THRESHOLD   = 0.015
        ROLLING_WINDOW   = 20
        MIN_AIR_FRAMES   = 2
        READY_KNEE_ANGLE = 160

        from collections import deque
        ankle_history            = deque(maxlen=ROLLING_WINDOW)
        in_air                   = False
        air_frame_count          = 0
        flight_times             = []
        frame_index              = 0
        cur_peak_y               = 1.0
        ground_knee_angles       = []
        knee_angles_landing_list = []
        valgus_ratios            = []
        symmetry_list            = []
        stability_scores         = []
        landing_frame            = None
        post_landing             = False
        recovery_times           = []

        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                break

            h, w = frame.shape[:2]
            rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # New API call
            mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            detection = detector.detect(mp_image)

            if detection.pose_landmarks and len(detection.pose_landmarks) > 0:
                raw = detection.pose_landmarks[0]
                lms = [_LM(lm.x, lm.y) for lm in raw]

                LH  = get_pt(lms, L_HIP,   w, h)
                RH  = get_pt(lms, R_HIP,   w, h)
                LK  = get_pt(lms, L_KNEE,  w, h)
                RK  = get_pt(lms, R_KNEE,  w, h)
                LA  = get_pt(lms, L_ANKLE, w, h)
                RA  = get_pt(lms, R_ANKLE, w, h)

                lay = get_y(lms, L_ANKLE)
                ray = get_y(lms, R_ANKLE)
                avg_ankle_y = (lay + ray) / 2

                lka = calc_angle(LH, LK, LA)
                rka = calc_angle(RH, RK, RA)
                avg_knee = (lka + rka) / 2

                ankle_history.append(avg_ankle_y)
                rolling_ground = max(ankle_history)
                airborne = avg_ankle_y < (rolling_ground - JUMP_THRESHOLD)

                if not airborne:
                    ground_knee_angles.append(avg_knee)

                if airborne and not in_air:
                    in_air = True
                    air_frame_count = 1
                    cur_peak_y = avg_ankle_y
                    post_landing = False

                elif airborne and in_air:
                    air_frame_count += 1
                    if avg_ankle_y < cur_peak_y:
                        cur_peak_y = avg_ankle_y

                elif not airborne and in_air:
                    in_air = False
                    if air_frame_count >= MIN_AIR_FRAMES:
                        flight_times.append(air_frame_count)
                        knee_angles_landing_list.append(avg_knee)

                        kw = abs(LK[0] - RK[0])
                        aw = abs(LA[0] - RA[0]) + 1e-6
                        valgus = kw / aw
                        valgus_ratios.append(valgus)

                        sym = 1 - abs(lka - rka) / 180
                        symmetry_list.append(sym)

                        if avg_knee < 120:     knee_sc = 100
                        elif avg_knee < 140:   knee_sc = 80
                        elif avg_knee < 160:   knee_sc = 50
                        else:                  knee_sc = 20

                        valgus_sc = 100 if valgus >= 0.90 else (60 if valgus >= 0.80 else 20)
                        sym_sc    = int(sym * 100)
                        stability = int(knee_sc*0.4 + valgus_sc*0.35 + sym_sc*0.25)
                        stability_scores.append(stability)
                        landing_frame = frame_index
                        post_landing  = True

                    air_frame_count = 0

                if post_landing and not airborne and landing_frame is not None:
                    if avg_knee >= READY_KNEE_ANGLE:
                        rec_s = (frame_index - landing_frame) / fps
                        recovery_times.append(rec_s)
                        post_landing  = False
                        landing_frame = None

            frame_index += 1

        cap.release()
        detector.close()

        if not flight_times:
            return {"error": "No valid jumps detected", "metrics": {}, "score": 0}

        heights_cm = [(9.81 * (f/fps)**2) / 8 * 100 for f in flight_times]
        best       = max(heights_cm)

        metrics = {
            "jumps_detected"     : len(flight_times),
            "best_jump_height_cm": round(best, 2),
            "avg_jump_height_cm" : round(float(np.mean(heights_cm)), 2),
            "best_flight_time_s" : round(max([f/fps for f in flight_times]), 3),
            "avg_flight_time_s"  : round(float(np.mean([f/fps for f in flight_times])), 3),
            "knee_flexion_deg"   : round(min(ground_knee_angles), 2) if ground_knee_angles else None,
            "landing_stability"  : round(float(np.mean(stability_scores)), 1) if stability_scores else None,
            "avg_knee_landing"   : round(float(np.mean(knee_angles_landing_list)), 2) if knee_angles_landing_list else None,
            "avg_valgus_ratio"   : round(float(np.mean(valgus_ratios)), 3) if valgus_ratios else None,
            "avg_symmetry_pct"   : round(float(np.mean(symmetry_list))*100, 1) if symmetry_list else None,
            "avg_recovery_time_s": round(float(np.mean(recovery_times)), 3) if recovery_times else None,
        }

        score = clamp(int((best / 35.0) * 60))
        return {"metrics": metrics, "score": score}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "metrics": {}, "score": 0}


# ══════════════════════════════════════════════════════════════════════════════
# TEST 3 — Shuttle Run
# ══════════════════════════════════════════════════════════════════════════════

def run_shuttle(video_path: str) -> dict:
    shuttle_dir = Path(__file__).resolve().parent.parent / 'ai_scripts' / 'shuttle_analysis'
    try:
        sys.path.insert(0, str(shuttle_dir))
        from core.shuttle_analyzer import analyze_video
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_out:
            result = analyze_video(str(video_path), output_dir=tmp_out)

        metrics = {
            "total_shuttle_legs" : result.total_shuttles,
            "total_time_s"       : result.total_time_s,
            "splits_s"           : result.splits,
            "peak_speed_ms"      : result.peak_speed_ms,
            "avg_speed_ms"       : result.avg_speed_ms,
            "peak_accel_ms2"     : result.peak_accel_ms2,
            "avg_decel_ms2"      : result.avg_decel_ms2,
            "calibration_px_per_m": result.calibration_px_per_m,
        }
        score = clamp(result.score)
        return {"metrics": metrics, "score": score}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "metrics": {}, "score": 0}
    finally:
        if str(shuttle_dir) in sys.path:
            sys.path.remove(str(shuttle_dir))


# ══════════════════════════════════════════════════════════════════════════════
# TEST 4 — 3-Colour Cone Picking
# Cone test is LIVE (camera-based), so the app submits the summary JSON
# directly. The backend just validates, stores and scores it.
# ══════════════════════════════════════════════════════════════════════════════

def run_cone(metrics_payload: dict) -> dict:
    try:
        print(">>> run_cone called")
        print(f">>> payload keys: {list(metrics_payload.keys())}")
        
        required = ['accuracy_percent', 'average_reaction_time', 'cognitive_score']
        for field in required:
            if field not in metrics_payload:
                return {"error": f"Missing field: {field}", "metrics": {}, "score": 0}

        print(">>> building metrics dict")
        
        hp = metrics_payload.get("hand_preference", {})
        hand_pref = "right" if isinstance(hp, dict) and hp.get("right_percent", 0) >= 50 else "left"

        metrics = {
            "num_trials"                 : metrics_payload.get("num_trials"),
            "accuracy_percent"           : metrics_payload.get("accuracy_percent"),
            "average_reaction_time"      : metrics_payload.get("average_reaction_time"),
            "fastest_reaction"           : metrics_payload.get("fastest_reaction"),
            "slowest_reaction"           : metrics_payload.get("slowest_reaction"),
            "average_movement_time"      : metrics_payload.get("average_movement_time"),
            "average_total_decision_time": metrics_payload.get("average_total_decision_time"),
            "reaction_time_std_dev"      : metrics_payload.get("reaction_time_std_dev"),
            "hand_preference"            : hand_pref,
            "hand_left_pct"              : hp.get("left_percent") if isinstance(hp, dict) else None,
            "hand_right_pct"             : hp.get("right_percent") if isinstance(hp, dict) else None,
            "decision_errors"            : metrics_payload.get("decision_errors"),
            "misses"                     : metrics_payload.get("misses"),
            "fatigue_index"              : metrics_payload.get("fatigue_index"),
            "cognitive_score"            : metrics_payload.get("cognitive_score"),
        }

        print(">>> computing score")
        score = clamp(metrics_payload.get("cognitive_score", 0))
        
        print(f">>> run_cone complete, score={score}")
        return {"metrics": metrics, "score": score}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e), "metrics": {}, "score": 0}

# ══════════════════════════════════════════════════════════════════════════════
# TEST 5 — Shadow Footwork
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# TEST 5 — Shadow Footwork
# All footwork-analysis logic (MediaPipe model, calibration, thresholds,
# scoring) lives in ai_scripts/footwork/footwork_analyzer.py — this just
# calls it and reshapes the result to match the standard run_* contract.
# ══════════════════════════════════════════════════════════════════════════════

def run_footwork(video_path: str, calibration_points=None) -> dict:
    footwork_dir = Path(__file__).resolve().parent.parent / 'ai_scripts' / 'footwork'
    try:
        sys.path.insert(0, str(footwork_dir))
        from footwork_analyzer import analyze_footwork

        result = analyze_footwork(str(video_path), calibration_points=calibration_points)

        if result["score"] is None:
            diag = result.get("diagnostics", {})
            return {
                "error": (
                    "No complete footwork sequence detected (all 6 corners must be reached). "
                    f"Diagnostics: {diag}"
                ),
                "metrics": {},
                "score": 0,
            }

        # metrics = full breakdown of the best sequence; every completed
        # rep is kept under all_sequences in case the caller wants them.
        metrics = dict(result["metrics"])
        metrics["all_sequences"] = result["sequences"]

        score = clamp(result["score"])
        return {"metrics": metrics, "score": score}

    except Exception as e:
        traceback.print_exc()
        result = run_footwork(video_path)
        print("FOOTWORK RESULT:", result)
        return {"error": str(e), "metrics": {}, "score": 0}
    finally:
        if str(footwork_dir) in sys.path:
            sys.path.remove(str(footwork_dir))

# ══════════════════════════════════════════════════════════════════════════════
# OVERALL SCORE — weighted across all 5 tests
# ══════════════════════════════════════════════════════════════════════════════

TEST_WEIGHTS = {
    "sprint"  : 0.20,
    "jump"    : 0.20,
    "shuttle" : 0.20,
    "cone"    : 0.20,
    "footwork": 0.20,
}

def compute_overall_score(test_results) -> float:
    """
    Given a queryset/list of TestResult objects,
    compute a weighted overall score (0-100).
    Only completed tests are included; weights are normalised.
    """
    scores   = {}
    for tr in test_results:
        if tr.status == 'completed' and tr.score is not None:
            scores[tr.test_type] = tr.score

    if not scores:
        return 0.0

    total_weight = sum(TEST_WEIGHTS[t] for t in scores)
    weighted_sum = sum(TEST_WEIGHTS[t] * s for t, s in scores.items())
    return round(weighted_sum / total_weight, 2)
