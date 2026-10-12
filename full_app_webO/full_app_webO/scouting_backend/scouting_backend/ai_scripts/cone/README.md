# Reaction Decision Test

A phone/webcam-based cognitive scouting tool. Athletes react to a
randomly displayed color by touching the matching cone. The app
measures reaction time, movement time, accuracy, consistency, hand
preference, and fatigue — not just physical speed.

## Setup

```bash
pip install -r requirements.txt
```

You'll need a webcam (or a phone used as a webcam) and three cones
in distinct colors (default: red, green, blue) placed within camera
view and within arm's reach of the athlete.

## Running

```bash
python main.py --player "Athlete Name" --trials 10
```

Arguments (both optional):
- `--player` — name used in the saved report filenames (default: `player`)
- `--trials` — number of trials in the session (default: 10, from `config.py`)

## Controls

- **SPACE** — during calibration, locks in cone positions once all three are visible
- **ESC** — quit at any time
- **r** — after a session finishes, press to restart with the same calibration

## How it works

1. **Calibration** — point the camera at all three cones. The app detects
   them by color and locks in their pixel positions once you press SPACE.
2. **Trials** — a random color appears on screen after a random 1–3s delay
   (so the athlete can't anticipate it). The athlete reacts by moving a
   hand to the matching cone.
3. **Timing** — MediaPipe Pose tracks wrist position every frame. The app
   separately measures:
   - **Reaction time**: cue appears → wrist starts moving
   - **Movement time**: wrist starts moving → wrist reaches the cone
   - **Total time**: cue appears → cone reached
4. **Scoring** — each trial is marked Correct / Wrong / Miss (timeout).
5. **Report** — after all trials, a summary is shown on screen and saved
   to `output/` as both JSON and CSV, including a composite 0–100
   "cognitive score" (40% accuracy, 30% raw speed, 20% consistency,
   10% fatigue resistance).

## Tuning cone detection to your lighting

Default HSV color ranges are in `config.py` under `COLOR_RANGES`, tuned
for generic red/green/blue cones under normal indoor lighting. If
calibration isn't reliably picking up your cones:

```bash
python tools/hsv_tuner.py
```

Point the camera at one cone at a time and drag the trackbars until only
that cone shows up white in the Mask window, then copy the printed
values into `config.py`.

## Project structure

```
reaction_test/
├── main.py                  # entry point / control loop
├── config.py                # all tunable constants
├── ui/
│   ├── screen.py             # on-screen drawing (cue, feedback, HUD, report)
│   └── timer.py              # time formatting helpers
├── detection/
│   ├── pose_detector.py      # MediaPipe Pose wrapper
│   └── cone_detector.py      # HSV color blob detection (calibration only)
├── tracking/
│   ├── wrist_tracker.py      # rolling wrist position/velocity history
│   └── movement.py           # movement-start + cone-selection logic
├── logic/
│   ├── trial_manager.py      # core state machine (PRE_CUE/CUE_ACTIVE/FEEDBACK/FINISHED)
│   ├── reaction_timer.py     # per-trial stopwatch
│   └── score.py              # running correct/wrong/miss count
├── metrics/
│   ├── statistics.py         # all scouting metrics + composite score
│   ├── fatigue.py            # first-half vs second-half RT comparison
│   └── consistency.py        # plain-language consistency label
├── reports/
│   ├── json_export.py
│   └── csv_export.py
├── tools/
│   └── hsv_tuner.py          # interactive HSV threshold finder
└── output/                   # saved session reports land here
```

## Notes / known limitations

- Selection detection uses a simple "wrist enters a fixed radius around
  the calibrated cone position" (Option A/C from the design doc). This
  means the camera and cones must stay still after calibration — if the
  camera moves, re-calibrate.
- Works best with cone colors that are visually distinct from the
  background and from skin tone/clothing. Avoid pointing the camera at
  anything red/green/blue in the background.
- `SAVE_ANNOTATED_VIDEO` in `config.py` can be turned on to also save
  an annotated `.mp4` of the session for coach review.

## Roadmap ideas (not yet built)

- Audio cues alongside the visual color cue
- Arrows/numbers/icons instead of plain colors for more complex decisions
- Secondary memory task layered on top of the reaction test
- YOLO-based cone/hand detection to support arbitrary training equipment
