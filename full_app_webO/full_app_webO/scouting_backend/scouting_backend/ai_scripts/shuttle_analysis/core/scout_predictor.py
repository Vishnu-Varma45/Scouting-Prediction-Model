"""
core/scout_predictor.py
========================
Converts raw shuttle-run metrics into a scouting prediction score,
performance tier, and actionable recommendation.

The model uses a weighted scoring rubric calibrated against
published elite/sub-elite 10 m shuttle benchmarks. Weights can
be overridden by supplying a JSON file (--model_weights).

Score = Σ (weight_i × normalised_metric_i)  ×  100
Normalised metric = clip((metric - worst) / (best - worst), 0, 1)

Higher score = better.
"""

import json
import math
from pathlib import Path
from typing import Dict, Any


# ── Default benchmark table ──────────────────────────────────
# (metric_key, weight, best_value, worst_value, invert)
# invert=True → lower is better (e.g. total time)
_DEFAULT_BENCHMARKS = [
    # metric                weight  best    worst   invert
    ("total_time_s",        0.30,   3.8,    7.5,    True),   # elite ~4 s for 10 m shuttle
    ("peak_speed_m_s",      0.20,   9.5,    4.0,    False),
    ("avg_decel_m_s2",      0.15,   12.0,   2.0,    False),  # higher decel = more explosive stop
    ("avg_accel_m_s2",      0.15,   11.0,   2.0,    False),
    ("stride_frequency_hz", 0.10,   4.5,    2.0,    False),
    ("stride_length_m",     0.05,   2.5,    0.8,    False),
    ("fatigue_index",       0.05,   -0.05,  0.30,   True),   # lower fatigue drift = better
]

_TIER_THRESHOLDS = [
    (90, "Elite",        "Outstanding. Ready for top-tier competition."),
    (75, "Pro Prospect", "Strong candidate. Address minor weaknesses."),
    (60, "Semi-Pro",     "Solid base. Targeted conditioning recommended."),
    (45, "Development",  "Needs structured speed & agility programme."),
    (0,  "Beginner",     "Fundamental conditioning required before scouting."),
]


class ScoutPredictor:

    def __init__(self, weights_path: str = "models/scout_weights.json"):
        self.benchmarks = self._load_weights(weights_path)

    # ── Public ───────────────────────────────────────────────
    def predict(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        score = self._compute_score(analysis)
        tier, recommendation = self._classify(score)
        agility = self._agility_index(analysis)

        return {
            "score": round(score, 2),
            "tier": tier,
            "recommendation": recommendation,
            "agility_index": round(agility, 3),
            "metric_breakdown": self._breakdown(analysis),
        }

    # ── Scoring ──────────────────────────────────────────────
    def _compute_score(self, a: Dict[str, Any]) -> float:
        total_weight = 0.0
        weighted_sum = 0.0

        for key, weight, best, worst, invert in self.benchmarks:
            val = a.get(key)
            if val is None or val == 0.0 and key != "fatigue_index":
                continue
            norm = self._normalise(val, best, worst, invert)
            weighted_sum += weight * norm
            total_weight += weight

        if total_weight == 0:
            return 0.0
        return (weighted_sum / total_weight) * 100.0

    @staticmethod
    def _normalise(val: float, best: float, worst: float, invert: bool) -> float:
        if invert:
            best, worst = worst, best  # flip so "best" side stays at 1.0
        span = best - worst
        if abs(span) < 1e-9:
            return 0.0
        norm = (val - worst) / span
        return max(0.0, min(1.0, norm))

    def _breakdown(self, a: Dict[str, Any]) -> Dict[str, float]:
        out = {}
        for key, weight, best, worst, invert in self.benchmarks:
            val = a.get(key, 0.0)
            norm = self._normalise(val, best, worst, invert)
            out[key] = round(norm * 100, 1)
        return out

    # ── Classification ───────────────────────────────────────
    @staticmethod
    def _classify(score: float):
        for threshold, tier, rec in _TIER_THRESHOLDS:
            if score >= threshold:
                return tier, rec
        return "Beginner", "Fundamental conditioning required."

    # ── Agility index ────────────────────────────────────────
    @staticmethod
    def _agility_index(a: Dict[str, Any]) -> float:
        """
        Composite agility index:
        AI = (avg_decel + avg_accel) / (2 × total_time / shuttle_count)
        Captures how explosive turns are relative to leg time.
        """
        decel = a.get("avg_decel_m_s2", 0.0)
        accel = a.get("avg_accel_m_s2", 0.0)
        total = a.get("total_time_s", 1.0)
        n = max(a.get("shuttle_count", 1), 1)
        leg_time = total / n
        if leg_time < 0.01:
            return 0.0
        return (decel + accel) / (2 * leg_time)

    # ── Weight loading ───────────────────────────────────────
    @staticmethod
    def _load_weights(path: str):
        p = Path(path)
        if p.exists():
            try:
                with open(p) as f:
                    data = json.load(f)
                return [
                    (d["key"], d["weight"], d["best"], d["worst"], d["invert"])
                    for d in data
                ]
            except Exception as e:
                print(f"[WARN] Could not load weights from {path}: {e}. Using defaults.")
        return _DEFAULT_BENCHMARKS
