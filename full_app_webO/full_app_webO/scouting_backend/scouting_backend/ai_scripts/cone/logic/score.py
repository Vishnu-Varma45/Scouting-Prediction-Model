"""
Running score state during a live session.
"""


class Score:
    def __init__(self):
        self.correct = 0
        self.wrong = 0
        self.misses = 0  # timed out with no selection

    @property
    def total(self):
        return self.correct + self.wrong + self.misses

    def record_correct(self):
        self.correct += 1

    def record_wrong(self):
        self.wrong += 1

    def record_miss(self):
        self.misses += 1

    def accuracy_percent(self):
        if self.total == 0:
            return 0.0
        return round(100 * self.correct / self.total, 1)

    def as_string(self):
        return f"Score: {self.correct}/{self.total}"
