"""
Turns a list of trial dicts (from TrialManager.trials) into the
scouting metrics described in the design doc.
"""
import statistics as pystats


def _valid_reaction_times(trials):
    return [t["reaction_time"] for t in trials if t["reaction_time"] is not None]


def _valid_movement_times(trials):
    return [t["movement_time"] for t in trials if t["movement_time"] is not None]


def _valid_total_times(trials):
    return [t["total_time"] for t in trials if t["total_time"] is not None]


def average_reaction_time(trials):
    rts = _valid_reaction_times(trials)
    return round(sum(rts) / len(rts), 3) if rts else None


def fastest_reaction(trials):
    rts = _valid_reaction_times(trials)
    return round(min(rts), 3) if rts else None


def slowest_reaction(trials):
    rts = _valid_reaction_times(trials)
    return round(max(rts), 3) if rts else None


def average_movement_time(trials):
    mts = _valid_movement_times(trials)
    return round(sum(mts) / len(mts), 3) if mts else None


def average_total_decision_time(trials):
    tts = _valid_total_times(trials)
    return round(sum(tts) / len(tts), 3) if tts else None


def accuracy_percent(trials):
    if not trials:
        return 0.0
    correct = sum(1 for t in trials if t["correct"])
    return round(100 * correct / len(trials), 1)


def hand_preference(trials):
    left = sum(1 for t in trials if t.get("hand_used") == "left_wrist")
    right = sum(1 for t in trials if t.get("hand_used") == "right_wrist")
    total = left + right
    if total == 0:
        return {"left_percent": 0.0, "right_percent": 0.0}
    return {
        "left_percent": round(100 * left / total, 1),
        "right_percent": round(100 * right / total, 1),
    }


def decision_errors(trials):
    return sum(1 for t in trials if t["picked"] is not None and not t["correct"])


def misses(trials):
    return sum(1 for t in trials if t["picked"] is None)


def reaction_time_std_dev(trials):
    """Standard deviation of reaction times = consistency measure (lower is better)."""
    rts = _valid_reaction_times(trials)
    if len(rts) < 2:
        return None
    return round(pystats.stdev(rts), 3)


def cognitive_score(trials, fatigue_index=None):
    """
    Weighted composite score (0-100) combining accuracy, raw reaction
    speed, consistency, and fatigue, per the weighting in the design doc:
    Accuracy 40%, Reaction 30%, Consistency 20%, Fatigue 10%.
    """
    acc = accuracy_percent(trials)  # already 0-100

    avg_rt = average_reaction_time(trials)
    # map reaction time to a 0-100 "speed score": 0.2s -> ~100, 1.0s -> ~0
    if avg_rt is None:
        speed_score = 0
    else:
        speed_score = max(0, min(100, 100 * (1.0 - avg_rt) / (1.0 - 0.2)))

    std_dev = reaction_time_std_dev(trials)
    # lower std dev is better: 0s -> 100, 0.5s+ -> 0
    if std_dev is None:
        consistency_score = 100
    else:
        consistency_score = max(0, min(100, 100 * (1 - std_dev / 0.5)))

    if fatigue_index is None:
        fatigue_score = 100
    else:
        # fatigue_index = (last-half avg RT - first-half avg RT); positive = slowing down
        fatigue_score = max(0, min(100, 100 * (1 - max(0, fatigue_index) / 0.5)))

    score = (
        0.40 * acc +
        0.30 * speed_score +
        0.20 * consistency_score +
        0.10 * fatigue_score
    )
    return round(score, 1)


def summarize(trials):
    """Single dict with every metric, ready to export."""
    from metrics.fatigue import fatigue_index

    fidx = fatigue_index(trials)
    return {
        "num_trials": len(trials),
        "accuracy_percent": accuracy_percent(trials),
        "average_reaction_time": average_reaction_time(trials),
        "fastest_reaction": fastest_reaction(trials),
        "slowest_reaction": slowest_reaction(trials),
        "average_movement_time": average_movement_time(trials),
        "average_total_decision_time": average_total_decision_time(trials),
        "reaction_time_std_dev": reaction_time_std_dev(trials),
        "hand_preference": hand_preference(trials),
        "decision_errors": decision_errors(trials),
        "misses": misses(trials),
        "fatigue_index": fidx,
        "cognitive_score": cognitive_score(trials, fidx),
    }
