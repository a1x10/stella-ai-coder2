"""Desktop and phone-control helpers for Stella AI Agent.

Desktop functions are best-effort wrappers around pyautogui and require a real
GUI session. The module itself is safe to import on headless servers: pyautogui
is imported lazily only when a desktop action is called. Phone functions require
Android Debug Bridge (`adb`) and an attached or network-connected Android
device/emulator.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


def _pyautogui() -> Any:
    """Import pyautogui lazily so headless CLI startup never crashes."""
    try:
        import pyautogui  # type: ignore

        pyautogui.FAILSAFE = True
        return pyautogui
    except Exception as exc:  # pragma: no cover - depends on host DISPLAY.
        raise RuntimeError(
            "pyautogui недоступен. Для GUI-инструментов нужен desktop session/DISPLAY; "
            f"исходная ошибка: {exc}"
        ) from exc


def move_mouse(x: int, y: int, duration: float = 0.2) -> dict[str, Any]:
    """Перемещает курсор мыши в указанные координаты."""
    pag = _pyautogui()
    pag.moveTo(x, y, duration=duration)
    return {"ok": True, "action": "move_mouse", "x": x, "y": y}


def click(x: int, y: int, button: str = "left") -> dict[str, Any]:
    """Кликает мышью в указанных координатах."""
    pag = _pyautogui()
    pag.click(x, y, button=button)
    return {"ok": True, "action": "click", "x": x, "y": y, "button": button}


def type_text(text: str, interval: float = 0.01) -> dict[str, Any]:
    """Вводит указанный текст."""
    pag = _pyautogui()
    pag.write(text, interval=interval)
    return {"ok": True, "action": "type_text", "chars": len(text)}


def press_key(key: str) -> dict[str, Any]:
    """Нажимает указанную клавишу."""
    pag = _pyautogui()
    pag.press(key)
    return {"ok": True, "action": "press_key", "key": key}


def hotkey(*args: str) -> dict[str, Any]:
    """Нажимает комбинацию клавиш."""
    pag = _pyautogui()
    pag.hotkey(*args)
    return {"ok": True, "action": "hotkey", "keys": list(args)}


def screenshot(filename: str = "screenshot.png") -> dict[str, Any]:
    """Делает скриншот экрана."""
    pag = _pyautogui()
    path = Path(filename).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    img = pag.screenshot()
    img.save(path)
    return {"ok": True, "action": "screenshot", "path": str(path), "size": img.size}


def get_screen_resolution() -> tuple[int, int]:
    """Возвращает разрешение экрана."""
    pag = _pyautogui()
    size = pag.size()
    return int(size.width), int(size.height)


def _adb_base(serial: str | None = None) -> list[str]:
    if not shutil.which("adb"):
        raise RuntimeError("adb не найден. Установите Android platform-tools и включите USB debugging.")
    cmd = ["adb"]
    if serial:
        cmd += ["-s", serial]
    return cmd


def adb_devices() -> dict[str, Any]:
    """Возвращает список Android-устройств, доступных через adb."""
    completed = subprocess.run(_adb_base() + ["devices", "-l"], text=True, capture_output=True, timeout=20)
    devices: list[dict[str, str]] = []
    for line in completed.stdout.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        devices.append({"serial": parts[0], "state": parts[1] if len(parts) > 1 else "unknown", "raw": line})
    return {"ok": completed.returncode == 0, "devices": devices, "stderr": completed.stderr}


def adb_shell(command: str, serial: str | None = None, timeout: int = 60) -> dict[str, Any]:
    """Выполняет adb shell-команду на подключённом телефоне/эмуляторе."""
    completed = subprocess.run(_adb_base(serial) + ["shell", command], text=True, capture_output=True, timeout=timeout)
    return {"ok": completed.returncode == 0, "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def adb_tap(x: int, y: int, serial: str | None = None) -> dict[str, Any]:
    """Тап по экрану Android-устройства."""
    return adb_shell(f"input tap {int(x)} {int(y)}", serial=serial)


def adb_swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300, serial: str | None = None) -> dict[str, Any]:
    """Свайп по экрану Android-устройства."""
    return adb_shell(f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {int(duration_ms)}", serial=serial)


def adb_text(text: str, serial: str | None = None) -> dict[str, Any]:
    """Ввод текста через adb input text. Пробелы кодируются как %s."""
    safe = str(text).replace(" ", "%s").replace("'", "")
    return adb_shell(f"input text '{safe}'", serial=serial)


def adb_keyevent(keycode: int | str, serial: str | None = None) -> dict[str, Any]:
    """Нажатие Android keyevent, например 3=HOME, 4=BACK, 66=ENTER."""
    return adb_shell(f"input keyevent {keycode}", serial=serial)


def adb_screenshot(filename: str = "phone_screenshot.png", serial: str | None = None) -> dict[str, Any]:
    """Снимает скриншот Android-устройства и сохраняет локально."""
    path = Path(filename).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(_adb_base(serial) + ["exec-out", "screencap", "-p"], capture_output=True, timeout=30)
    if completed.returncode != 0:
        return {"ok": False, "returncode": completed.returncode, "stderr": completed.stderr.decode("utf-8", errors="replace")}
    path.write_bytes(completed.stdout)
    return {"ok": True, "path": str(path), "bytes": len(completed.stdout)}


def visual_qa_metadata(image_path: str) -> dict[str, Any]:
    """Возвращает базовые метаданные скриншота для smoke-проверки visual QA."""
    try:
        from PIL import Image

        img = Image.open(image_path)
        return {"ok": True, "path": str(Path(image_path).resolve()), "width": img.width, "height": img.height, "mode": img.mode}
    except Exception as exc:
        return {"ok": False, "path": image_path, "error": str(exc)}


if __name__ == "__main__":
    payload = {"adb": adb_devices() if shutil.which("adb") else "adb not installed"}
    try:
        payload["screen"] = get_screen_resolution()
    except Exception as exc:
        payload["screen"] = f"desktop unavailable: {exc}"
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print("GUI-инструменты загружены. FAILSAFE включён при наличии pyautogui desktop session.")
    time.sleep(1)
