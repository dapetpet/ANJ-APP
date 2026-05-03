from __future__ import annotations

import threading
import time
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

from timing import PeriodicSchedule, format_countdown


R_INTERVAL_S = 10.0
WF_INTERVAL_S = 30.0
WF_GAP_S = 0.1


class KeyBackend:
    def __init__(self) -> None:
        try:
            import keyboard
        except Exception as e:
            raise RuntimeError(
                "ç¼ºå°ä¾èµ keyboardãè¯·åè¿è¡ï¼pip install -r requirements.txt"
            ) from e
        self._keyboard = keyboard

    def press_once(self, key: str) -> None:
        self._keyboard.press_and_release(key)

    def register_hotkey(self, hotkey: str, callback) -> None:
        self._keyboard.add_hotkey(hotkey, callback, suppress=False, trigger_on_release=False)

    def unregister_all_hotkeys(self) -> None:
        self._keyboard.unhook_all_hotkeys()
        self._keyboard.unhook_all()


def send_wf(backend: KeyBackend) -> None:
    backend.press_once("w")
    time.sleep(WF_GAP_S)
    backend.press_once("f")


def send_r(backend: KeyBackend) -> None:
    backend.press_once("r")


@dataclass
class EngineState:
    r_schedule: PeriodicSchedule
    wf_schedule: PeriodicSchedule
    running: bool = False


class AutoKeyEngine:
    def __init__(self, backend: KeyBackend) -> None:
        self._backend = backend
        self._lock = threading.Lock()
        self._stop_event: threading.Event | None = None
        self._threads: list[threading.Thread] = []
        self._state = EngineState(
            r_schedule=PeriodicSchedule(interval_s=R_INTERVAL_S),
            wf_schedule=PeriodicSchedule(interval_s=WF_INTERVAL_S),
            running=False,
        )

    def snapshot(self) -> EngineState:
        with self._lock:
            return EngineState(
                r_schedule=PeriodicSchedule(
                    interval_s=self._state.r_schedule.interval_s,
                    next_run=self._state.r_schedule.next_run,
                ),
                wf_schedule=PeriodicSchedule(
                    interval_s=self._state.wf_schedule.interval_s,
                    next_run=self._state.wf_schedule.next_run,
                ),
                running=self._state.running,
            )

    def start(self) -> None:
        with self._lock:
            if self._state.running:
                return
            self._stop_event = threading.Event()
            now = time.monotonic()
            self._state.r_schedule.start_immediately(now)
            self._state.wf_schedule.start_immediately(now)
            self._state.running = True

            self._threads = [
                threading.Thread(
                    target=self._loop_r,
                    name="autokey-r",
                    daemon=True,
                ),
                threading.Thread(
                    target=self._loop_wf,
                    name="autokey-wf",
                    daemon=True,
                ),
            ]
            for t in self._threads:
                t.start()

    def stop(self) -> None:
        threads: list[threading.Thread]
        stop_event: threading.Event | None
        with self._lock:
            stop_event = self._stop_event
            threads = list(self._threads)
            self._stop_event = None
            self._threads = []
            self._state.running = False
            self._state.r_schedule.reset()
            self._state.wf_schedule.reset()

        if stop_event is not None:
            stop_event.set()
        for t in threads:
            t.join(timeout=1.0)

    def toggle(self) -> None:
        if self.snapshot().running:
            self.stop()
        else:
            self.start()

    def _get_stop_event(self) -> threading.Event:
        with self._lock:
            if self._stop_event is None:
                self._stop_event = threading.Event()
            return self._stop_event

    def _sleep_until(self, target_monotonic: float) -> bool:
        stop_event = self._get_stop_event()
        while True:
            now = time.monotonic()
            remaining = target_monotonic - now
            if remaining <= 0:
                return not stop_event.is_set()
            if stop_event.wait(min(remaining, 0.5)):
                return False

    def _loop_r(self) -> None:
        stop_event = self._get_stop_event()
        while not stop_event.is_set():
            with self._lock:
                next_run = self._state.r_schedule.next_run
            if next_run is None:
                with self._lock:
                    self._state.r_schedule.start(time.monotonic())
                    next_run = self._state.r_schedule.next_run
            if next_run is None:
                continue
            if not self._sleep_until(next_run):
                break
            if stop_event.is_set():
                break
            send_r(self._backend)
            with self._lock:
                self._state.r_schedule.advance(time.monotonic())

    def _loop_wf(self) -> None:
        stop_event = self._get_stop_event()
        while not stop_event.is_set():
            with self._lock:
                next_run = self._state.wf_schedule.next_run
            if next_run is None:
                with self._lock:
                    self._state.wf_schedule.start(time.monotonic())
                    next_run = self._state.wf_schedule.next_run
            if next_run is None:
                continue
            if not self._sleep_until(next_run):
                break
            if stop_event.is_set():
                break
            send_wf(self._backend)
            with self._lock:
                self._state.wf_schedule.advance(time.monotonic())


class App:
    def __init__(self, root: tk.Tk) -> None:
        self._root = root
        self._root.title("AutoKey")
        self._root.resizable(False, False)

        self._backend = KeyBackend()
        self._engine = AutoKeyEngine(self._backend)

        self._status_var = tk.StringVar(value="Stopped")
        self._r_cd_var = tk.StringVar(value="--")
        self._wf_cd_var = tk.StringVar(value="--")

        self._build_ui()
        self._register_hotkeys()
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._tick()

    def _build_ui(self) -> None:
        style = ttk.Style(self._root)
        if "vista" in style.theme_names():
            style.theme_use("vista")

        frame = ttk.Frame(self._root, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")

        ttk.Label(frame, text="Status:").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, textvariable=self._status_var, width=12).grid(
            row=0, column=1, sticky="w"
        )

        ttk.Label(frame, text="Next R:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Label(frame, textvariable=self._r_cd_var, width=12).grid(
            row=1, column=1, sticky="w", pady=(8, 0)
        )

        ttk.Label(frame, text="Next WF:").grid(
            row=2, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(frame, textvariable=self._wf_cd_var, width=12).grid(
            row=2, column=1, sticky="w", pady=(4, 0)
        )

        btns = ttk.Frame(frame)
        btns.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        btns.columnconfigure(0, weight=1)
        btns.columnconfigure(1, weight=1)

        ttk.Button(btns, text="Start", command=self.start).grid(
            row=0, column=0, sticky="ew", padx=(0, 6)
        )
        ttk.Button(btns, text="Stop", command=self.stop).grid(
            row=0, column=1, sticky="ew", padx=(6, 0)
        )

        ttk.Separator(frame).grid(row=4, column=0, columnspan=2, sticky="ew", pady=12)
        ttk.Label(frame, text="Hotkeys: F8 Start/Pause, F9 Stop").grid(
            row=5, column=0, columnspan=2, sticky="w"
        )

    def _register_hotkeys(self) -> None:
        def on_f8():
            self._root.after(0, self.toggle)

        def on_f9():
            self._root.after(0, self.stop)

        self._backend.register_hotkey("F8", on_f8)
        self._backend.register_hotkey("F9", on_f9)

    def start(self) -> None:
        self._engine.start()

    def stop(self) -> None:
        self._engine.stop()

    def toggle(self) -> None:
        self._engine.toggle()

    def _tick(self) -> None:
        snap = self._engine.snapshot()
        self._status_var.set("Running" if snap.running else "Stopped")

        now = time.monotonic()
        self._r_cd_var.set(format_countdown(snap.r_schedule.remaining(now)))
        self._wf_cd_var.set(format_countdown(snap.wf_schedule.remaining(now)))

        self._root.after(200, self._tick)

    def _on_close(self) -> None:
        self.stop()
        self._backend.unregister_all_hotkeys()
        self._root.destroy()


def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
