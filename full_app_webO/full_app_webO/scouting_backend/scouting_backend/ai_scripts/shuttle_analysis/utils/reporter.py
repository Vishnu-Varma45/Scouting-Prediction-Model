"""
utils/reporter.py
==================
Saves analysis results to JSON and CSV formats.
"""

import json
import csv
from pathlib import Path
from typing import Dict, Any
from datetime import datetime


class Reporter:

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ── JSON ─────────────────────────────────────────────────
    def save_json(self, data: Dict[str, Any], filename: str) -> Path:
        out = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "analysis": data,
        }
        path = self.output_dir / filename
        with open(path, "w") as f:
            json.dump(out, f, indent=2)
        return path

    # ── CSV ──────────────────────────────────────────────────
    def save_csv(self, analysis: Dict[str, Any], filename: str) -> Path:
        """Write scalar metrics to a flat CSV (one row per metric)."""
        path = self.output_dir / filename
        skip_keys = {"speed_profile", "timestamps_s", "turn_times_s", "split_times_s"}

        rows = []
        for k, v in analysis.items():
            if k in skip_keys:
                continue
            if isinstance(v, (int, float, str, bool)):
                rows.append({"metric": k, "value": v})

        # Expand split times
        for i, s in enumerate(analysis.get("split_times_s", []), 1):
            rows.append({"metric": f"split_{i}_s", "value": s})

        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["metric", "value"])
            writer.writeheader()
            writer.writerows(rows)

        return path

    # ── Speed CSV (for charting) ─────────────────────────────
    def save_speed_profile_csv(self, analysis: Dict[str, Any], filename: str) -> Path:
        path = self.output_dir / filename
        times = analysis.get("timestamps_s", [])
        speeds = analysis.get("speed_profile", [])
        length = min(len(times), len(speeds))

        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["time_s", "speed_m_s"])
            writer.writeheader()
            for i in range(length):
                writer.writerow({"time_s": times[i], "speed_m_s": speeds[i]})
        return path
