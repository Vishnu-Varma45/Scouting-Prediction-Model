"""
Reaction Decision Test — main entry point.

Run:
    python main.py [--player NAME] [--trials N]

Controls:
    SPACE   lock in cone calibration once all 3 cones are visible
    ESC     quit at any time
    r       restart the test after it finishes
"""
import argparse
import time
import cv2

from config import (
    CAMERA_INDEX, FRAME_WIDTH, FRAME_HEIGHT, NUM_TRIALS,
    OUTPUT_DIR, SAVE_ANNOTATED_VIDEO,
)
from detection.pose_detector import PoseDetector
from detection.cone_detector import find_all_cones
from tracking.wrist_tracker import WristTracker
from logic.trial_manager import TrialManager
from metrics.statistics import summarize
from reports.json_export import export_json
from reports.csv_export import export_csv
from ui import screen


def calibrate(cap):
    """
    Live-detect cone colors until the user presses SPACE with all
    three cones visible. Returns the locked-in {"Red": (x,y), ...}.
    """
    locked_positions = {"Red": None, "Green": None, "Blue": None}

    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        frame = cv2.flip(frame, 1)

        detected = find_all_cones(frame)
        display = screen.draw_calibration_overlay(frame.copy(), detected)
        cv2.imshow("Reaction Decision Test", display)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            return None
        if key == 32:  # SPACE
            if all(pos is not None for pos in detected.values()):
                locked_positions = detected
                return locked_positions
            # else: not all cones visible yet, keep waiting


def run_test(cap, cone_positions, num_trials, player_name):
    pose_detector = PoseDetector()
    wrist_tracker = WristTracker()
    trial_manager = TrialManager(cone_positions, num_trials=num_trials)

    video_writer = None
    if SAVE_ANNOTATED_VIDEO:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(
            f"{OUTPUT_DIR}/{player_name}_annotated.mp4", fourcc, 20.0,
            (FRAME_WIDTH, FRAME_HEIGHT),
        )

    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        frame = cv2.flip(frame, 1)

        pose_result = pose_detector.process(frame)
        wrist_tracker.update(pose_result)

        if not trial_manager.is_finished():
            trial_manager.update(wrist_tracker)

        display = frame.copy()
        if pose_result:
            display = pose_detector.draw(display, pose_result["raw_landmarks"])
        display = screen.draw_cone_markers(display, cone_positions)

        if trial_manager.state == "CUE_ACTIVE":
            display = screen.draw_cue(display, trial_manager.current_target)
        elif trial_manager.state == "FEEDBACK":
            display = screen.draw_cue(display, trial_manager.current_target)
            display = screen.draw_feedback(display, trial_manager.last_result)
        elif trial_manager.state == "FINISHED":
            summary = summarize(trial_manager.trials)
            display = screen.draw_final_report(display, summary)

        if trial_manager.state != "FINISHED":
            display = screen.draw_hud(
                display, trial_manager.score, trial_manager.trial_index, num_trials
            )

        if video_writer is not None:
            video_writer.write(display)

        cv2.imshow("Reaction Decision Test", display)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            break
        if trial_manager.state == "FINISHED" and key == ord('r'):
            trial_manager = TrialManager(cone_positions, num_trials=num_trials)

    pose_detector.close()
    if video_writer is not None:
        video_writer.release()

    return trial_manager


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--player", default="player")
    parser.add_argument("--trials", type=int, default=NUM_TRIALS)
    args = parser.parse_args()

    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    if not cap.isOpened():
        print("Could not open camera. Check CAMERA_INDEX in config.py.")
        return

    print("Starting calibration. Show all 3 colored cones, then press SPACE.")
    cone_positions = calibrate(cap)

    if cone_positions is None:
        print("Calibration cancelled.")
        cap.release()
        cv2.destroyAllWindows()
        return

    print(f"Calibrated: {cone_positions}")
    trial_manager = run_test(cap, cone_positions, args.trials, args.player)

    cap.release()
    cv2.destroyAllWindows()

    if trial_manager.trials:
        summary = summarize(trial_manager.trials)
        json_path = export_json(trial_manager.trials, summary,
                                 output_dir=OUTPUT_DIR, player_name=args.player)
        csv_path = export_csv(trial_manager.trials,
                               output_dir=OUTPUT_DIR, player_name=args.player)
        print("\n--- SESSION SUMMARY ---")
        for k, v in summary.items():
            print(f"{k}: {v}")
        print(f"\nSaved: {json_path}")
        print(f"Saved: {csv_path}")


if __name__ == "__main__":
    main()
