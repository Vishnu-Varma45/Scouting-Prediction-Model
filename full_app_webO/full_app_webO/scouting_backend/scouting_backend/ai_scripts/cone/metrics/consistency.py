"""
Helpers for describing reaction-time consistency in plain language,
useful for the printed report / coach-facing summary.
"""
from metrics.statistics import reaction_time_std_dev


def consistency_label(trials):
    std_dev = reaction_time_std_dev(trials)
    if std_dev is None:
        return "Not enough data"
    if std_dev < 0.08:
        return "Excellent"
    if std_dev < 0.15:
        return "Good"
    if std_dev < 0.25:
        return "Fair"
    return "Poor"
