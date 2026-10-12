"""
The core state machine for the Reaction Decision Test.

States:
    CALIBRATING   -> waiting for cone positions to be locked in
    PRE_CUE       -> random delay before the cue appears (anti-anticipation)
    CUE_ACTIVE    -> cue is showing, waiting for movement + selection
    FEEDBACK      -> briefly showing correct/wrong before next trial
    FINISHED      -> all trials complete

Call `update()` once per frame with the latest wrist_tracker and cone
positions; read `.state` / `.current_target` / `.last_result` to drive
the UI.
"""
import random
import time

from config import (
    NUM_TRIALS, MIN_CUE_DELAY, MAX_CUE_DELAY, TRIAL_TIMEOUT,
    INTER_TRIAL_PAUSE, COLOR_RANGES,
)
from logic.reaction_timer import ReactionTimer
from logic.score import Score
from tracking.movement import has_movement_started, detect_selected_cone


class TrialManager:
    def __init__(self, cone_positions, num_trials=NUM_TRIALS):
        self.cone_positions = cone_positions
        self.num_trials = num_trials
        self.colors = list(COLOR_RANGES.keys())

        self.score = Score()
        self.trials = []          # list of completed trial dicts
        self.trial_index = 0

        self.state = "PRE_CUE"
        self.state_entered_at = time.time()
        self.pre_cue_delay = random.uniform(MIN_CUE_DELAY, MAX_CUE_DELAY)

        self.current_target = None
        self.timer = ReactionTimer()
        self.last_result = None  # "Correct" / "Wrong" / "Miss"

    # -----------------------------------------------------------
    def _enter_state(self, new_state):
        self.state = new_state
        self.state_entered_at = time.time()

    def _time_in_state(self):
        return time.time() - self.state_entered_at

    # -----------------------------------------------------------
    def update(self, wrist_tracker):
        if self.state == "FINISHED":
            return

        if self.state == "PRE_CUE":
            if self._time_in_state() >= self.pre_cue_delay:
                self.current_target = random.choice(self.colors)
                self.timer = ReactionTimer()
                self.timer.start()
                self._enter_state("CUE_ACTIVE")
            return

        if self.state == "CUE_ACTIVE":
            # 1. movement initiation
            if self.timer.movement_start_time is None and has_movement_started(wrist_tracker):
                self.timer.mark_movement_start()

            # 2. cone selection
            picked_color, picked_hand = detect_selected_cone(wrist_tracker, self.cone_positions)
            if picked_color is not None:
                self.timer.mark_selection()
                if self.timer.movement_start_time is None:
                    # selection happened without us catching movement onset;
                    # backfill so reaction_time isn't None
                    self.timer.movement_start_time = self.timer.cue_time
                self._finish_trial(picked_color, picked_hand)
                return

            # 3. timeout -> miss
            if self.timer.elapsed_since_cue() >= TRIAL_TIMEOUT:
                self._finish_trial(picked_color=None, picked_hand=None)
                return
            return

        if self.state == "FEEDBACK":
            if self._time_in_state() >= INTER_TRIAL_PAUSE:
                self.trial_index += 1
                if self.trial_index >= self.num_trials:
                    self._enter_state("FINISHED")
                else:
                    self.pre_cue_delay = random.uniform(MIN_CUE_DELAY, MAX_CUE_DELAY)
                    self._enter_state("PRE_CUE")
            return

    # -----------------------------------------------------------
    def _finish_trial(self, picked_color, picked_hand):
        correct = (picked_color == self.current_target)

        if picked_color is None:
            self.last_result = "Miss"
            self.score.record_miss()
        elif correct:
            self.last_result = "Correct"
            self.score.record_correct()
        else:
            self.last_result = "Wrong"
            self.score.record_wrong()

        self.trials.append({
            "trial": self.trial_index + 1,
            "target": self.current_target,
            "picked": picked_color,
            "hand_used": picked_hand,
            "correct": bool(correct) if picked_color else False,
            "reaction_time": self.timer.reaction_time,
            "movement_time": self.timer.movement_time,
            "total_time": self.timer.total_time,
        })
        self._enter_state("FEEDBACK")

    # -----------------------------------------------------------
    def is_finished(self):
        return self.state == "FINISHED"
