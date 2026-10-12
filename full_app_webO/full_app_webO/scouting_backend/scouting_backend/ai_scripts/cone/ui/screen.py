"""
All the on-screen drawing lives here so main.py stays focused on the
control loop. Everything is drawn directly onto the camera frame with
OpenCV shapes/text.
"""
import cv2
from config import DRAW_COLORS, CONE_SELECTION_RADIUS


def draw_calibration_overlay(frame, cone_positions):
    for color, pos in cone_positions.items():
        if pos is None:
            continue
        draw_color = DRAW_COLORS.get(color, DRAW_COLORS["White"])
        cv2.circle(frame, pos, 12, draw_color, -1)
        cv2.circle(frame, pos, CONE_SELECTION_RADIUS, draw_color, 2)
        cv2.putText(frame, color, (pos[0] - 20, pos[1] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, draw_color, 2)

    cv2.putText(frame, "Calibrating... show all 3 cones, press SPACE to lock",
                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, DRAW_COLORS["White"], 2)
    return frame


def draw_cue(frame, target_color):
    if target_color is None:
        return frame
    draw_color = DRAW_COLORS.get(target_color, DRAW_COLORS["White"])
    h, w = frame.shape[:2]
    cx = w // 2
    cy = 90
    cv2.circle(frame, (cx, cy), 55, draw_color, -1)
    cv2.putText(frame, target_color, (cx - 50, cy + 90),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1, draw_color, 3)
    return frame


def draw_feedback(frame, result):
    h, w = frame.shape[:2]
    if result == "Correct":
        text, color = "CORRECT", DRAW_COLORS["Correct"]
    elif result == "Wrong":
        text, color = "WRONG", DRAW_COLORS["Wrong"]
    else:
        text, color = "MISS", DRAW_COLORS["Wrong"]
    cv2.putText(frame, text, (w // 2 - 120, h // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 2.0, color, 4)
    return frame


def draw_hud(frame, score, trial_index, num_trials, avg_rt=None):
    h, w = frame.shape[:2]
    y = h - 60
    cv2.putText(frame, f"{score.as_string()}  Trial {min(trial_index + 1, num_trials)}/{num_trials}",
                (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, DRAW_COLORS["White"], 2)
    if avg_rt is not None:
        cv2.putText(frame, f"Avg RT: {avg_rt:.2f}s",
                    (20, y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, DRAW_COLORS["White"], 2)
    return frame


def draw_cone_markers(frame, cone_positions):
    for color, pos in cone_positions.items():
        if pos is None:
            continue
        draw_color = DRAW_COLORS.get(color, DRAW_COLORS["White"])
        cv2.circle(frame, pos, CONE_SELECTION_RADIUS, draw_color, 2)
    return frame


def draw_final_report(frame, summary):
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (20, 20, 20), -1)
    frame = cv2.addWeighted(overlay, 0.75, frame, 0.25, 0)

    lines = [
        "TEST COMPLETE",
        f"Accuracy: {summary['accuracy_percent']}%",
        f"Avg Reaction Time: {summary['average_reaction_time']}s",
        f"Fastest / Slowest: {summary['fastest_reaction']}s / {summary['slowest_reaction']}s",
        f"Avg Movement Time: {summary['average_movement_time']}s",
        f"Consistency (std dev): {summary['reaction_time_std_dev']}",
        f"Fatigue Index: {summary['fatigue_index']}",
        f"Cognitive Score: {summary['cognitive_score']} / 100",
        "",
        "Press ESC to quit",
    ]
    y = 80
    for line in lines:
        cv2.putText(frame, line, (60, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    DRAW_COLORS["White"], 2)
        y += 40
    return frame
