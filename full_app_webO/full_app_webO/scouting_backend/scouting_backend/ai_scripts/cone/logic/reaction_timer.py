"""
Small stopwatch helper. The trial manager creates one of these per
trial to time cue-appearance -> movement-start -> cone-touch.
"""
import time


class ReactionTimer:
    def __init__(self):
        self.cue_time = None
        self.movement_start_time = None
        self.selection_time = None

    def start(self):
        self.cue_time = time.time()
        self.movement_start_time = None
        self.selection_time = None

    def mark_movement_start(self):
        if self.movement_start_time is None:
            self.movement_start_time = time.time()

    def mark_selection(self):
        if self.selection_time is None:
            self.selection_time = time.time()

    @property
    def reaction_time(self):
        """Cue appears -> movement starts."""
        if self.cue_time is None or self.movement_start_time is None:
            return None
        return round(self.movement_start_time - self.cue_time, 3)

    @property
    def movement_time(self):
        """Movement starts -> cone touched."""
        if self.movement_start_time is None or self.selection_time is None:
            return None
        return round(self.selection_time - self.movement_start_time, 3)

    @property
    def total_time(self):
        """Cue appears -> cone touched."""
        if self.cue_time is None or self.selection_time is None:
            return None
        return round(self.selection_time - self.cue_time, 3)

    def elapsed_since_cue(self):
        if self.cue_time is None:
            return 0.0
        return time.time() - self.cue_time
