# Shuttle Run Analysis — 10 m AI Scouting Model

A modular Python pipeline that analyses a **10 m shuttle run video** and outputs
biomechanical metrics + a scouting prediction score for your AI model.

## Project Structure

```
shuttle_analysis/
├── main.py                        # CLI entry point
├── requirements.txt
├── README.md
├── core/
│   ├── video_processor.py         # OpenCV video wrapper
│   ├── pose_tracker.py            # Motion tracking (background subtraction)
│   ├── shuttle_analyzer.py        # Turn detection, speed, splits, kinematics
│   └── scout_predictor.py         # Weighted scouting score & tier
├── utils/
│   ├── reporter.py                # JSON + CSV output
│   └── visualizer.py             # Annotated video renderer
├── models/
│   └── scout_weights.json         # Tunable benchmark weights
└── output/                        # Generated outputs (auto-created)
    ├── shuttle_report.json
    ├── shuttle_metrics.csv
    ├── speed_profile.csv
    └── shuttle_annotated.mp4
```

## Quick Start

```bash
pip install -r requirements.txt

python main.py --video path/to/video.mp4 --distance 10
```

## Key Arguments

| Flag | Default | Description |
|------|---------|-------------|
| `--video` | `input/Shuttle_run.mp4` | Path to input video |
| `--distance` | `10.0` | Shuttle distance in metres |
| `--calibration_px` | auto | Pixels per metre (auto if omitted) |
| `--output_dir` | `output` | Output directory |
| `--no_video` | False | Skip annotated video (faster) |
| `--model_weights` | `models/scout_weights.json` | Custom scouting weights |

## Metrics Produced

| Metric | Description |
|--------|-------------|
| `total_time_s` | Total test duration |
| `split_times_s` | Per-leg time list |
| `avg_speed_m_s` | Mean running speed |
| `peak_speed_m_s` | Max instantaneous speed |
| `avg_decel_m_s2` | Mean deceleration entering turns |
| `avg_accel_m_s2` | Mean acceleration exiting turns |
| `stride_frequency_hz` | Steps per second |
| `stride_length_m` | Estimated stride length |
| `fatigue_index` | Drift in split times (0 = no fatigue) |

## Scouting Score

Weighted 0–100 composite:

```
30% total time  +  20% peak speed  +  15% decel  +  15% accel
+  10% stride freq  +  5% stride length  +  5% fatigue
```

**Tiers:** Elite (≥90) | Pro Prospect (≥75) | Semi-Pro (≥60) | Development (≥45) | Beginner

## Customising Weights

Edit `models/scout_weights.json` to adjust benchmarks for your sport/age group.

## MediaPipe Upgrade (Optional)

For full skeletal pose tracking, install the mediapipe model file:

```
models/pose_landmarker_lite.task   # download from MediaPipe model hub
```

Then switch `core/pose_tracker.py` to use `PoseLandmarker` via `mp.tasks.vision`.
