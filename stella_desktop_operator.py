"""Full Desktop Operator helpers for Stella AI Agent 3.8.

The module is intentionally safe to import on headless servers. Real desktop
control is performed only when a function is called and a GUI session is
available. Every helper returns structured JSON-friendly data and writes to the
same operator log used by Stella Autopilot when a project root is provided.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import platform
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

try:
    from stella_autopilot_tools import append_operator_log
except Exception:  # pragma: no cover - module can be used standalone.
    append_operator_log = None  # type: ignore[assignment]


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _root(root: str | Path | None = None) -> Path:
    return Path(root or Path.cwd()).expanduser().resolve()


def _log(root: str | Path | None, event: str, data: dict[str, Any]) -> None:
    if append_operator_log is None:
        return
    try:
        append_operator_log(_root(root), event, data)  # type: ignore[misc]
    except Exception:
        return


def _pyautogui() -> Any:
    """Import pyautogui lazily so CLI startup never crashes on headless hosts."""
    try:
        import pyautogui  # type: ignore

        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05
        return pyautogui
    except Exception as exc:  # pragma: no cover - depends on host DISPLAY.
        raise RuntimeError(
            "Desktop GUI недоступен. Нужен реальный экран/DISPLAY/Wayland session; "
            f"исходная ошибка: {exc}"
        ) from exc


def _pygetwindow() -> Any | None:
    try:
        import pygetwindow  # type: ignore

        return pygetwindow
    except Exception:
        return None


def _psutil() -> Any | None:
    try:
        import psutil  # type: ignore

        return psutil
    except Exception:
        return None


def desktop_status(root: str | Path | None = None) -> dict[str, Any]:
    """Return capabilities and environment state for desktop control."""
    payload: dict[str, Any] = {
        "ok": True,
        "time": _now(),
        "platform": platform.platform(),
        "system": platform.system(),
        "display": os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY") or "",
        "session": os.environ.get("XDG_SESSION_TYPE") or "",
        "tools": {
            "pyautogui": False,
            "pygetwindow": _pygetwindow() is not None,
            "psutil": _psutil() is not None,
            "tesseract": bool(shutil.which("tesseract")),
            "xdotool": bool(shutil.which("xdotool")),
            "wmctrl": bool(shutil.which("wmctrl")),
            "open": bool(shutil.which("open")),
            "powershell": bool(shutil.which("powershell") or shutil.which("pwsh")),
        },
        "screen": None,
        "note": "Desktop actions need a visible unlocked desktop session. Headless import is supported.",
    }
    try:
        pag = _pyautogui()
        size = pag.size()
        pos = pag.position()
        payload["tools"]["pyautogui"] = True
        payload["screen"] = {"width": int(size.width), "height": int(size.height), "mouse_x": int(pos.x), "mouse_y": int(pos.y)}
    except Exception as exc:
        payload["desktop_error"] = str(exc)
    _log(root, "desktop_status", payload)
    return payload


def screenshot(root: str | Path | None = None, filename: str = "desktop_screenshot.png") -> dict[str, Any]:
    """Capture the visible desktop screen to a file."""
    pag = _pyautogui()
    out = _root(root) / ".stella" / "screenshots" / filename
    if Path(filename).is_absolute():
        out = Path(filename)
    out.parent.mkdir(parents=True, exist_ok=True)
    img = pag.screenshot()
    img.save(out)
    payload = {"ok": True, "path": str(out), "width": img.width, "height": img.height, "mode": getattr(img, "mode", "")}
    _log(root, "desktop_screenshot", payload)
    return payload


def screen_ocr(root: str | Path | None = None, image_path: str = "", lang: str = "eng+rus") -> dict[str, Any]:
    """Run OCR over a screenshot or a supplied image path if pytesseract/tesseract exists."""
    if not image_path:
        shot = screenshot(root=root, filename="desktop_ocr_source.png")
        image_path = shot["path"]
    if not shutil.which("tesseract"):
        payload = {"ok": False, "error": "tesseract не найден. Установите Tesseract OCR для распознавания текста на экране.", "image_path": image_path}
        _log(root, "desktop_ocr_unavailable", payload)
        return payload
    try:
        from PIL import Image
        import pytesseract  # type: ignore

        text = pytesseract.image_to_string(Image.open(image_path), lang=lang)
        payload = {"ok": True, "image_path": str(Path(image_path).resolve()), "lang": lang, "text": text[:20000]}
        _log(root, "desktop_ocr", {**payload, "text": text[:2000]})
        return payload
    except Exception as exc:
        payload = {"ok": False, "error": str(exc), "image_path": image_path}
        _log(root, "desktop_ocr_error", payload)
        return payload


def list_windows(root: str | Path | None = None) -> dict[str, Any]:
    """List visible windows using pygetwindow, wmctrl or AppleScript depending on OS."""
    windows: list[dict[str, Any]] = []
    gw = _pygetwindow()
    if gw is not None:
        try:
            for index, win in enumerate(gw.getAllWindows()):
                title = getattr(win, "title", "") or ""
                if not title.strip():
                    continue
                windows.append({
                    "index": index,
                    "title": title,
                    "left": getattr(win, "left", None),
                    "top": getattr(win, "top", None),
                    "width": getattr(win, "width", None),
                    "height": getattr(win, "height", None),
                    "active": bool(getattr(win, "isActive", False)),
                    "minimized": bool(getattr(win, "isMinimized", False)),
                    "maximized": bool(getattr(win, "isMaximized", False)),
                })
            payload = {"ok": True, "source": "pygetwindow", "windows": windows[:500]}
            _log(root, "desktop_windows", {"count": len(windows), "source": "pygetwindow"})
            return payload
        except Exception:
            pass
    if shutil.which("wmctrl"):
        completed = subprocess.run(["wmctrl", "-lG"], text=True, capture_output=True, timeout=15)
        for line in completed.stdout.splitlines():
            parts = line.split(maxsplit=7)
            if len(parts) >= 8:
                windows.append({"id": parts[0], "desktop": parts[1], "left": parts[2], "top": parts[3], "width": parts[4], "height": parts[5], "host": parts[6], "title": parts[7]})
        payload = {"ok": completed.returncode == 0, "source": "wmctrl", "windows": windows[:500], "stderr": completed.stderr}
        _log(root, "desktop_windows", {"count": len(windows), "source": "wmctrl"})
        return payload
    payload = {"ok": False, "windows": [], "error": "Не найден pygetwindow/wmctrl или текущая ОС не отдаёт список окон."}
    _log(root, "desktop_windows_unavailable", payload)
    return payload


def focus_window(root: str | Path | None = None, title_contains: str = "", index: int | None = None) -> dict[str, Any]:
    """Focus/activate a window by title fragment or index."""
    gw = _pygetwindow()
    if gw is not None:
        wins = [w for w in gw.getAllWindows() if (getattr(w, "title", "") or "").strip()]
        target = None
        if index is not None and 0 <= int(index) < len(wins):
            target = wins[int(index)]
        elif title_contains:
            lower = title_contains.lower()
            target = next((w for w in wins if lower in (getattr(w, "title", "") or "").lower()), None)
        if target is None:
            return {"ok": False, "error": "Окно не найдено.", "title_contains": title_contains, "index": index}
        if getattr(target, "isMinimized", False):
            target.restore()
        target.activate()
        payload = {"ok": True, "title": getattr(target, "title", ""), "action": "focus_window"}
        _log(root, "desktop_focus_window", payload)
        return payload
    if shutil.which("wmctrl") and title_contains:
        completed = subprocess.run(["wmctrl", "-a", title_contains], text=True, capture_output=True, timeout=15)
        payload = {"ok": completed.returncode == 0, "title_contains": title_contains, "stderr": completed.stderr}
        _log(root, "desktop_focus_window", payload)
        return payload
    return {"ok": False, "error": "Фокусировка окна недоступна без pygetwindow/wmctrl."}


def running_apps(root: str | Path | None = None, limit: int = 250) -> dict[str, Any]:
    """List currently running processes/apps without exposing command-line secrets by default."""
    ps = _psutil()
    apps: list[dict[str, Any]] = []
    if ps is not None:
        for proc in ps.process_iter(["pid", "name", "username", "status", "create_time"]):
            try:
                info = proc.info
                apps.append({
                    "pid": info.get("pid"),
                    "name": info.get("name"),
                    "user": info.get("username"),
                    "status": info.get("status"),
                })
            except Exception:
                continue
        apps = sorted(apps, key=lambda x: str(x.get("name") or "").lower())[: max(1, min(int(limit), 1000))]
        payload = {"ok": True, "source": "psutil", "apps": apps}
        _log(root, "desktop_running_apps", {"count": len(apps)})
        return payload
    completed = subprocess.run("ps -eo pid,comm --no-headers | head -300", shell=True, text=True, capture_output=True, timeout=15)
    for line in completed.stdout.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2:
            apps.append({"pid": parts[0], "name": parts[1]})
    payload = {"ok": completed.returncode == 0, "source": "ps", "apps": apps, "stderr": completed.stderr}
    _log(root, "desktop_running_apps", {"count": len(apps), "source": "ps"})
    return payload


def app_inventory(root: str | Path | None = None, limit: int = 500) -> dict[str, Any]:
    """Best-effort list of installed/launchable desktop applications."""
    system = platform.system().lower()
    apps: list[dict[str, str]] = []
    if system == "linux":
        dirs = [Path("/usr/share/applications"), Path.home() / ".local/share/applications"]
        for folder in dirs:
            if not folder.exists():
                continue
            for item in folder.glob("*.desktop"):
                try:
                    text = item.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                name = ""
                exec_cmd = ""
                for line in text.splitlines():
                    if line.startswith("Name=") and not name:
                        name = line.split("=", 1)[1]
                    elif line.startswith("Exec=") and not exec_cmd:
                        exec_cmd = line.split("=", 1)[1]
                if name:
                    apps.append({"name": name, "path": str(item), "exec": exec_cmd})
    elif system == "darwin":
        for folder in [Path("/Applications"), Path.home() / "Applications"]:
            if folder.exists():
                for item in folder.glob("*.app"):
                    apps.append({"name": item.stem, "path": str(item), "exec": f"open -a {item.stem}"})
    elif system == "windows":
        roots = [os.environ.get("ProgramData", ""), os.environ.get("APPDATA", "")]
        for base in [Path(r) for r in roots if r]:
            for item in base.rglob("*.lnk"):
                apps.append({"name": item.stem, "path": str(item), "exec": str(item)})
                if len(apps) >= limit:
                    break
    payload = {"ok": True, "system": system, "apps": apps[: max(1, min(int(limit), 2000))]}
    _log(root, "desktop_app_inventory", {"count": len(payload["apps"]), "system": system})
    return payload


def launch_app(root: str | Path | None = None, name_or_path: str = "", args: str = "") -> dict[str, Any]:
    """Launch an application by path/name using the OS launcher."""
    if not name_or_path.strip():
        return {"ok": False, "error": "Не указано приложение."}
    system = platform.system().lower()
    if system == "windows":
        cmd = f'start "" {name_or_path} {args}'
    elif system == "darwin":
        if Path(name_or_path).exists():
            cmd = f'open {json.dumps(name_or_path)} --args {args}'
        else:
            cmd = f'open -a {json.dumps(name_or_path)} --args {args}'
    else:
        desktop_match = None
        for app in app_inventory(root=root, limit=2000).get("apps", []):
            if name_or_path.lower() in app.get("name", "").lower():
                desktop_match = app
                break
        if desktop_match and shutil.which("gtk-launch"):
            cmd = f"gtk-launch {Path(desktop_match['path']).stem}"
        else:
            cmd = f"{name_or_path} {args}".strip()
    subprocess.Popen(cmd, cwd=_root(root), shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    payload = {"ok": True, "action": "launch_app", "name_or_path": name_or_path, "args": args, "command": cmd}
    _log(root, "desktop_launch_app", payload)
    return payload


def mouse_action(root: str | Path | None = None, action: str = "click", x: int | None = None, y: int | None = None, button: str = "left", clicks: int = 1, duration: float = 0.15) -> dict[str, Any]:
    """Move/click/double-click/right-click at screen coordinates."""
    pag = _pyautogui()
    action = (action or "click").lower().strip()
    if x is not None and y is not None:
        pag.moveTo(int(x), int(y), duration=max(0.0, float(duration)))
    if action == "move":
        pass
    elif action == "click":
        pag.click(button=button, clicks=max(1, int(clicks)))
    elif action == "double_click":
        pag.doubleClick(button=button)
    elif action == "right_click":
        pag.rightClick()
    elif action == "middle_click":
        pag.middleClick()
    else:
        return {"ok": False, "error": "action должен быть move/click/double_click/right_click/middle_click"}
    pos = pag.position()
    payload = {"ok": True, "action": action, "x": int(pos.x), "y": int(pos.y), "button": button, "clicks": clicks}
    _log(root, "desktop_mouse_action", payload)
    return payload


def drag_mouse(root: str | Path | None = None, x: int = 0, y: int = 0, duration: float = 0.4, button: str = "left") -> dict[str, Any]:
    pag = _pyautogui()
    pag.dragTo(int(x), int(y), duration=max(0.0, float(duration)), button=button)
    payload = {"ok": True, "action": "drag_mouse", "x": int(x), "y": int(y), "duration": duration, "button": button}
    _log(root, "desktop_drag_mouse", payload)
    return payload


def scroll(root: str | Path | None = None, clicks: int = -5, x: int | None = None, y: int | None = None) -> dict[str, Any]:
    pag = _pyautogui()
    if x is not None and y is not None:
        pag.moveTo(int(x), int(y), duration=0.1)
    pag.scroll(int(clicks))
    payload = {"ok": True, "action": "scroll", "clicks": int(clicks)}
    _log(root, "desktop_scroll", payload)
    return payload


def keyboard_action(root: str | Path | None = None, action: str = "press", text: str = "", keys: list[str] | str | None = None, interval: float = 0.01) -> dict[str, Any]:
    """Type text, press a key or trigger a hotkey combination."""
    pag = _pyautogui()
    action = (action or "press").lower().strip()
    if isinstance(keys, str):
        key_list = [k.strip() for k in keys.replace("+", ",").split(",") if k.strip()]
    elif isinstance(keys, list):
        key_list = [str(k) for k in keys]
    else:
        key_list = []
    if action == "type":
        pag.write(text, interval=max(0.0, float(interval)))
        payload = {"ok": True, "action": "type", "chars": len(text)}
    elif action == "press":
        key = key_list[0] if key_list else text
        if not key:
            return {"ok": False, "error": "Нужна клавиша для press."}
        pag.press(key)
        payload = {"ok": True, "action": "press", "key": key}
    elif action == "hotkey":
        if not key_list:
            return {"ok": False, "error": "Нужен список клавиш для hotkey."}
        pag.hotkey(*key_list)
        payload = {"ok": True, "action": "hotkey", "keys": key_list}
    else:
        return {"ok": False, "error": "action должен быть type/press/hotkey"}
    _log(root, "desktop_keyboard_action", payload)
    return payload


def wait(root: str | Path | None = None, seconds: float = 1.0) -> dict[str, Any]:
    seconds = max(0.0, min(float(seconds), 60.0))
    time.sleep(seconds)
    payload = {"ok": True, "action": "wait", "seconds": seconds}
    _log(root, "desktop_wait", payload)
    return payload


def close_focused_window(root: str | Path | None = None) -> dict[str, Any]:
    """Close focused window via standard hotkey; caller should require approval."""
    system = platform.system().lower()
    pag = _pyautogui()
    if system == "darwin":
        pag.hotkey("command", "w")
    else:
        pag.hotkey("alt", "f4")
    payload = {"ok": True, "action": "close_focused_window", "system": system}
    _log(root, "desktop_close_focused_window", payload)
    return payload


def run_desktop_sequence(root: str | Path | None = None, steps: list[dict[str, Any]] | str | None = None, dry_run: bool = True) -> dict[str, Any]:
    """Run or preview a short desktop macro sequence.

    Supported actions: status, screenshot, launch_app, focus_window, mouse,
    keyboard, scroll, wait, ocr. Real execution should be approval-gated by the
    caller; dry_run returns a normalized plan only.
    """
    if isinstance(steps, str):
        steps_obj = json.loads(steps) if steps.strip() else []
    else:
        steps_obj = steps or []
    if not isinstance(steps_obj, list):
        return {"ok": False, "error": "steps должен быть списком объектов."}
    normalized = [{"index": i + 1, **(step if isinstance(step, dict) else {"action": str(step)})} for i, step in enumerate(steps_obj)]
    if dry_run:
        payload = {"ok": True, "dry_run": True, "steps": normalized}
        _log(root, "desktop_sequence_dry_run", payload)
        return payload
    results: list[dict[str, Any]] = []
    for step in normalized[:100]:
        action = str(step.get("action", "")).lower().strip()
        if action == "status":
            results.append(desktop_status(root))
        elif action == "screenshot":
            results.append(screenshot(root, filename=str(step.get("filename") or "desktop_sequence.png")))
        elif action == "launch_app":
            results.append(launch_app(root, str(step.get("name_or_path") or step.get("app") or ""), str(step.get("args") or "")))
        elif action == "focus_window":
            results.append(focus_window(root, title_contains=str(step.get("title_contains") or ""), index=step.get("index")))
        elif action == "mouse":
            results.append(mouse_action(root, action=str(step.get("mouse_action") or "click"), x=step.get("x"), y=step.get("y"), button=str(step.get("button") or "left"), clicks=int(step.get("clicks") or 1)))
        elif action == "keyboard":
            results.append(keyboard_action(root, action=str(step.get("keyboard_action") or "press"), text=str(step.get("text") or ""), keys=step.get("keys")))
        elif action == "scroll":
            results.append(scroll(root, clicks=int(step.get("clicks") or -5), x=step.get("x"), y=step.get("y")))
        elif action == "wait":
            results.append(wait(root, seconds=float(step.get("seconds") or 1)))
        elif action == "ocr":
            results.append(screen_ocr(root, image_path=str(step.get("image_path") or ""), lang=str(step.get("lang") or "eng+rus")))
        else:
            results.append({"ok": False, "error": f"Неизвестный action: {action}", "step": step})
            break
    payload = {"ok": all(bool(r.get("ok")) for r in results), "dry_run": False, "results": results}
    _log(root, "desktop_sequence", {"ok": payload["ok"], "count": len(results)})
    return payload


if __name__ == "__main__":
    print(json.dumps(desktop_status(), ensure_ascii=False, indent=2))
