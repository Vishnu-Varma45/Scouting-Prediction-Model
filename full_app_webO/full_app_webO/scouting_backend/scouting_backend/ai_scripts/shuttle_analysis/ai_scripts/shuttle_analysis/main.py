"""
Shuttle Run Analysis - Main Entry Point
========================================
Analyses a shuttle run video (default: 30 ft / 9.144 m drill) and outputs:
  - Per-leg split times
  - Total shuttle time
  - Deceleration / acceleration metrics
  - Scout performance score
  - Annotated output video
  - JSON + CSV reports

Usage:
    python main.py input/Shuttle_run.mp4
    python main.py input/Shuttle_run.mp4 --output results/
"""

import argparse
import sys
from pathlib import Path

# shuttle_analyzer.py must be in the same directory as main.py
from core.shuttle_analyzer import analyze_video


def parse_args():
    parser = argparse.ArgumentParser(description="Shuttle Run Analysis (30 ft two-cone drill)")
    parser.add_argument(
        "video",
        nargs="?",
        default="input/Shuttle_run.mp4",
        help="Path to input video file (default: input/Shuttle_run.mp4)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output",
        help="Directory for all outputs (default: output/)",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"[ERROR] Video not found: {video_path}")
        print("  Make sure you pass the correct path, e.g.:")
        print("      python main.py input/Shuttle_run.mp4")
        sys.exit(1)

    # analyze_video() handles everything:
    #   - pose tracking (MediaPipe)
    #   - calibration
    #   - kinematics (speed, acceleration)
    #   - cone-event detection
    #   - annotated video rendering
    #   - JSON + CSV reports
    #   - scout score
    result = analyze_video(str(video_path), output_dir=args.output)

    # result is an AnalysisResult dataclass — return it for programmatic use
    return result


if __name__ == "__main__":
    main()