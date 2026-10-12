"""
Wraps MediaPipe Pose so the rest of the app only deals with simple
(x, y) pixel coordinates for the landmarks we care about.
Updated to use mediapipe tasks API (mp.solutions removed in newer versions).
"""
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
import urllib.request
from pathlib import Path
from config import POSE_DETECTION_CONFIDENCE, POSE_TRACKING_CONFIDENCE

# ── Model path — reuse the one downloaded by sprint ───────────────────────────
_MODEL_PATH = (
    Path(__file__).resolve().parent.parent.parent
    / 'sprint' / 'pose_landmarker_heavy.task'
)

def _ensure_model():
    if not _MODEL_PATH.exists():
        print(f"Downloading pose model to {_MODEL_PATH} ...")
        urllib.request.urlretrieve(
            "https://storage.googleapis.com/mediapipe-models/"
            "pose_landmarker/pose_landmarker_heavy/float16/latest/"
            "pose_landmarker_heavy.task",
            str(_MODEL_PATH)
        )
        print("Download complete.")

# ── Landmark index constants (replaces mp.solutions.pose.PoseLandmark) ────────
class _PoseLandmark:
    LEFT_WRIST      = 15
    RIGHT_WRIST     = 16
    LEFT_ELBOW      = 13
    RIGHT_ELBOW     = 14
    LEFT_SHOULDER   = 11
    RIGHT_SHOULDER  = 12
    LEFT_HIP        = 23
    RIGHT_HIP       = 24
    LEFT_KNEE       = 25
    RIGHT_KNEE      = 26
    LEFT_ANKLE      = 27
    RIGHT_ANKLE     = 28

class PoseDetector:
    def __init__(self):
        _ensure_model()
        options = vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(
                model_asset_path=str(_MODEL_PATH)
            ),
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=POSE_DETECTION_CONFIDENCE,
            min_pose_presence_confidence=POSE_DETECTION_CONFIDENCE,
            min_tracking_confidence=POSE_TRACKING_CONFIDENCE,
        )
        self._detector     = vision.PoseLandmarker.create_from_options(options)
        self.landmark_names = _PoseLandmark()

    def process(self, frame_bgr):
        """
        Returns a dict with pixel coordinates for the landmarks we track,
        or None if no person was detected.
        """
        h, w = frame_bgr.shape[:2]
        rgb  = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

        mp_image  = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        detection = self._detector.detect(mp_image)

        if not detection.pose_landmarks or len(detection.pose_landmarks) == 0:
            return None

        raw = detection.pose_landmarks[0]
        L   = self.landmark_names

        def px(idx):
            lm = raw[idx]
            return (
                int(lm.x * w),
                int(lm.y * h),
                getattr(lm, 'visibility', 1.0)
            )

        return {
            "left_wrist"    : px(L.LEFT_WRIST),
            "right_wrist"   : px(L.RIGHT_WRIST),
            "left_elbow"    : px(L.LEFT_ELBOW),
            "right_elbow"   : px(L.RIGHT_ELBOW),
            "left_shoulder" : px(L.LEFT_SHOULDER),
            "right_shoulder": px(L.RIGHT_SHOULDER),
            # raw_landmarks kept for compatibility — now a simple list of lm objects
            "raw_landmarks" : raw,
        }

    def draw(self, frame_bgr, raw_landmarks):
        """
        Drawing is a no-op in server mode — no display window on Django.
        Kept for API compatibility with cone main.py.
        """
        return frame_bgr

    def close(self):
        self._detector.close()