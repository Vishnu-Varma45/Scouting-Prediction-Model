"""
Compares reaction time in the first half of the session vs the
second half. A positive fatigue_index means the athlete is slowing
down (getting worse) as the session goes on.
"""


def fatigue_index(trials):
    rts = [t["reaction_time"] for t in trials if t["reaction_time"] is not None]
    if len(rts) < 4:
        return None

    mid = len(rts) // 2
    first_half = rts[:mid]
    second_half = rts[mid:]

    first_avg = sum(first_half) / len(first_half)
    second_avg = sum(second_half) / len(second_half)

    return round(second_avg - first_avg, 3)
