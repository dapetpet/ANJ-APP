from __future__ import annotations

from dataclasses import dataclass


def format_countdown(seconds: float | None) -> str:
    if seconds is None:
        return "--"
    if seconds <= 0:
        return "00:00"
    total = int(seconds)
    mm, ss = divmod(total, 60)
    return f"{mm:02d}:{ss:02d}"


@dataclass
class PeriodicSchedule:
    interval_s: float
    next_run: float | None = None

    def start(self, now: float) -> None:
        self.next_run = now + self.interval_s

    def remaining(self, now: float) -> float | None:
        if self.next_run is None:
            return None
        return max(0.0, self.next_run - now)

    def advance(self, now: float) -> None:
        self.next_run = now + self.interval_s

    def reset(self) -> None:
        self.next_run = None
