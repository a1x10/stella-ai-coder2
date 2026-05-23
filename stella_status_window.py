"""Always-on-top status overlay for Stella AI Agent.

The overlay is intentionally best-effort: on desktop systems it shows a small
"Stella AI работает..." window; on headless servers or Python builds without
Tkinter it silently degrades to a no-op so the CLI never crashes during
deploy/SSH/test tasks.
"""

from __future__ import annotations

import threading
from typing import Any

try:  # Tkinter is an OS-level optional dependency on many Linux servers.
    import tkinter as tk  # type: ignore
except Exception:  # pragma: no cover - depends on host OS packages.
    tk = None  # type: ignore


class StellaStatusWindow:
    def __init__(self) -> None:
        self.root: Any = None
        self.window: Any = None
        self.label: Any = None
        self._available = False
        self._lock = threading.RLock()
        if tk is None:
            return
        try:
            self.root = tk.Tk()
            self.root.withdraw()
            self.window = tk.Toplevel(self.root)
            self.window.title("Stella AI")
            self.window.attributes("-topmost", True)
            self.window.overrideredirect(True)
            self.window.configure(bg="#2E3440")
            self.label = tk.Label(
                self.window,
                text="Stella AI работает...",
                font=("Arial", 12, "bold"),
                fg="#ECEFF4",
                bg="#2E3440",
                padx=20,
                pady=10,
            )
            self.label.pack(expand=True, fill="both")
            self.window.withdraw()
            self._position_window()
            self._available = True
        except Exception:
            self._available = False
            self.root = None
            self.window = None
            self.label = None

    def _position_window(self) -> None:
        if not self.root or not self.window:
            return
        try:
            self.root.update_idletasks()
            width = 340
            height = 56
            screen_width = self.root.winfo_screenwidth()
            x = max(0, screen_width - width - 24)
            y = 24
            self.window.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass

    def start(self, message: str = "Stella AI работает... Пожалуйста, подождите") -> None:
        if not self._available or not self.window:
            return
        with self._lock:
            try:
                self.update_message(message)
                self.window.deiconify()
                self.window.lift()
                if self.root:
                    self.root.update()
            except Exception:
                pass

    def update_message(self, message: str) -> None:
        if not self._available or not self.label:
            return
        with self._lock:
            try:
                clipped = str(message)
                if len(clipped) > 72:
                    clipped = clipped[:69] + "..."
                self.label.config(text=clipped)
                if self.root:
                    self.root.update_idletasks()
                    self.root.update()
            except Exception:
                pass

    def stop(self) -> None:
        if not self._available or not self.window:
            return
        with self._lock:
            try:
                self.window.withdraw()
                if self.root:
                    self.root.update()
            except Exception:
                pass

    def destroy(self) -> None:
        if not self._available:
            return
        try:
            if self.window:
                self.window.destroy()
            if self.root:
                self.root.destroy()
        except Exception:
            pass
        finally:
            self._available = False


if __name__ == "__main__":
    import time

    status = StellaStatusWindow()
    status.start("Stella AI работает... Пожалуйста, подождите")
    time.sleep(2)
    status.update_message("Stella AI выполняет инструмент...")
    time.sleep(2)
    status.stop()
    status.destroy()
