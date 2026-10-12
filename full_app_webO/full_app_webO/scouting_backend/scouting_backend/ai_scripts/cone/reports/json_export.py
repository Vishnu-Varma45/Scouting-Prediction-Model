import json
import os
import time


def export_json(trials, summary, output_dir="output", player_name="player"):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{player_name}_{timestamp}.json"
    path = os.path.join(output_dir, filename)

    payload = {
        "player_name": player_name,
        "timestamp": timestamp,
        "summary": summary,
        "trials": trials,
    }

    with open(path, "w") as f:
        json.dump(payload, f, indent=2)

    return path
