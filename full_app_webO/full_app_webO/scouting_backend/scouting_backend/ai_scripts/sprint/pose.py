import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
import urllib.request
import os
from pathlib import Path

# ── Download the pose landmarker model if not already present ──────────────────
_MODEL_URL  = (
    "https://storage.googleapis.com/mediapipe-models/"
    "pose_landmarker/pose_landmarker_heavy/float16/latest/"
    "pose_landmarker_heavy.task"
)
_MODEL_PATH = Path(__file__).resolve().parent / "pose_landmarker_heavy.task"

def _ensure_model():
    if not _MODEL_PATH.exists():
        print(f"Downloading MediaPipe pose model to {_MODEL_PATH} ...")
        urllib.request.urlretrieve(_MODEL_URL, str(_MODEL_PATH))
        print("Download complete.")

# ── Compatibility shim — mimics the old mp.solutions.pose interface ───────────
class _PoseLandmark:
    """Maps landmark names to indices — same as the old mp.solutions.pose.PoseLandmark."""
    NOSE            = 0
    LEFT_EYE        = 1
    RIGHT_EYE       = 2
    LEFT_EAR        = 3
    RIGHT_EAR       = 4
    LEFT_SHOULDER   = 11
    RIGHT_SHOULDER  = 12
    LEFT_ELBOW      = 13
    RIGHT_ELBOW     = 14
    LEFT_WRIST      = 15
    RIGHT_WRIST     = 16
    LEFT_HIP        = 23
    RIGHT_HIP       = 24
    LEFT_KNEE       = 25
    RIGHT_KNEE      = 26
    LEFT_ANKLE      = 27
    RIGHT_ANKLE     = 28
    LEFT_HEEL       = 29
    RIGHT_HEEL      = 30
    LEFT_FOOT_INDEX = 31
    RIGHT_FOOT_INDEX= 32

class _FakeLandmark:
    """Mimics a single landmark object with .x .y .z .visibility"""
    def __init__(self, x=0.0, y=0.0, z=0.0, visibility=0.0):
        self.x          = x
        self.y          = y
        self.z          = z
        self.visibility = visibility

class _FakePoseLandmarks:
    """Mimics result.pose_landmarks.landmark list."""
    def __init__(self, landmarks_list):
        self.landmark = landmarks_list

class _FakeResult:
    """Mimics the old Pose.process() result object."""
    def __init__(self, pose_landmarks):
        self.pose_landmarks = pose_landmarks

class _PoseDetector:
    """
    Drop-in replacement for mp.solutions.pose.Pose().
    Uses the new mediapipe Tasks API under the hood but exposes
    the same .process(rgb_frame) → result interface.
    """
    def __init__(self):
        _ensure_model()
        options = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(
                model_asset_path=str(_MODEL_PATH)
            ),
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._detector = vision.PoseLandmarker.create_from_options(options)

    def process(self, rgb_frame):
        """
        Accepts an RGB numpy array (same as old API).
        Returns a _FakeResult that mimics the old result object.
        """
        import numpy as np
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame
        )
        detection = self._detector.detect(mp_image)

        if not detection.pose_landmarks or len(detection.pose_landmarks) == 0:
            return _FakeResult(pose_landmarks=None)

        # Convert new NormalizedLandmark list to shim objects
        raw = detection.pose_landmarks[0]   # first (only) person
        landmarks = [
            _FakeLandmark(
                x=lm.x,
                y=lm.y,
                z=lm.z,
                visibility=getattr(lm, 'visibility', 1.0)
            )
            for lm in raw
        ]
        return _FakeResult(
            pose_landmarks=_FakePoseLandmarks(landmarks)
        )

    def close(self):
        self._detector.close()

class _PoseModule:
    """Mimics the mp.solutions.pose module namespace."""
    Pose          = _PoseDetector
    PoseLandmark  = _PoseLandmark
    POSE_CONNECTIONS = []   # not used in sprint analyzer

# ── Public API — called by analyzer.py ────────────────────────────────────────
def get_pose_detector():
    return _PoseDetector()

def get_pose_module():
    return _PoseModule()