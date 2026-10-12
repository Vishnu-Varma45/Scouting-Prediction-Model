import csv
import os
import time

def export_csv(trials, output_dir="output", player_name="player"):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{player_name}_{timestamp}.csv"
    path = os.path.join(output_dir, filename)

    fieldnames = [
        "trial", "target", "picked", "hand_used", "correct",
        "reaction_time", "movement_time", "total_time",
    ]

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in trials:
            writer.writerow({k: t.get(k) for k in fieldnames})

    return path
