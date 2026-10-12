"""
Tiny helpers for formatting elapsed/remaining time for on-screen display.
"""


def format_seconds(seconds):
    if seconds is None:
        return "--"
    return f"{seconds:.2f}s"


def countdown_text(elapsed, total):
    remaining = max(0.0, total - elapsed)
    return f"{remaining:.1f}s"
