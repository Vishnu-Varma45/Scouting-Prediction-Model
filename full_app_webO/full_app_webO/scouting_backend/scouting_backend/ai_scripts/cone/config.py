"""
Central configuration for the Reaction Decision Test.
Tune these values to match your camera, lighting, and cone setup.
"""
# Camera
CAMERA_INDEX = 0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

# Cone colors (HSV thresholds for OpenCV color detection)
# Tune these to your actual cones under your actual lighting.
# Use tools/hsv_tuner.py (created below) to find good values.
COLOR_RANGES = {
    "Red": [
        # red wraps around the HSV hue circle, so two ranges
        ((0, 120, 70), (10, 255, 255)),
        ((170, 120, 70), (180, 255, 255)),
    ],
    "Green": [
        ((40, 70, 70), (85, 255, 255)),
    ],
    "Blue": [
        ((90, 80, 60), (130, 255, 255)),
    ],
}

# Minimum contour area (in pixels) to accept a color blob as a cone
MIN_CONE_CONTOUR_AREA = 800

# Radius (px) of the invisible "selection zone" around each calibrated cone
CONE_SELECTION_RADIUS = 60

# Pose / wrist tracking
POSE_DETECTION_CONFIDENCE = 0.5
POSE_TRACKING_CONFIDENCE = 0.5

# Wrist speed (pixels/second) above which we consider the athlete
# to have "started moving" toward a cone
MOVEMENT_SPEED_THRESHOLD = 400

# Smoothing window (frames) for wrist velocity calculation
VELOCITY_SMOOTHING_FRAMES = 3

# Trial engine
NUM_TRIALS = 10
MIN_CUE_DELAY = 1.0   # seconds, minimum random delay before a cue appears
MAX_CUE_DELAY = 3.0   # seconds, maximum random delay before a cue appears
TRIAL_TIMEOUT = 5.0   # seconds, max time to wait for a selection before marking a miss
INTER_TRIAL_PAUSE = 1.5  # seconds, pause after feedback before next trial

# Output
OUTPUT_DIR = "output"
SAVE_ANNOTATED_VIDEO = False

# Colors for drawing (BGR, since OpenCV uses BGR not RGB)
DRAW_COLORS = {
    "Red": (0, 0, 255),
    "Green": (0, 200, 0),
    "Blue": (255, 100, 0),
    "White": (255, 255, 255),
    "Black": (0, 0, 0),
    "Correct": (0, 220, 0),
    "Wrong": (0, 0, 220),
}
