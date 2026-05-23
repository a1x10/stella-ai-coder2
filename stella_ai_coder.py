#!/usr/bin/env python3
"""
Stella AI Agent 3.8 Enterprise Autopilot

Original terminal AI coding agent for local-first software work.
It is inspired by the broad public category of terminal coding agents, but it does
not copy proprietary UI text, branding, or private implementation details from
any commercial product.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html as html_lib
import json
import os
import platform
import uuid
import re
import shlex
import shutil
import subprocess
import sys
import textwrap
import threading
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import requests
from rich import box

from stella_status_window import StellaStatusWindow
from rich.align import Align
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from stella_gui_tools import move_mouse, click, type_text, press_key, hotkey, screenshot, get_screen_resolution, adb_devices, adb_shell, adb_tap, adb_swipe, adb_text, adb_keyevent, adb_screenshot, visual_qa_metadata
from stella_security_tools import check_sql_injection, check_xss
from stella_bot_sandbox import BotSandbox, load_handler
from stella_autopilot_tools import make_operator_plan, research as autopilot_research, github_scan as autopilot_github_scan, draft_report as autopilot_draft_report, create_connector_profile, install_pixel_agents as autopilot_install_pixel_agents, make_live_viewer, append_operator_log, classify_task, prepare_telegram_action, home_assistant_call
from stella_desktop_operator import desktop_status as desktop_operator_status, list_windows as desktop_operator_list_windows, focus_window as desktop_operator_focus_window, running_apps as desktop_operator_running_apps, app_inventory as desktop_operator_app_inventory, launch_app as desktop_operator_launch_app, screenshot as desktop_operator_screenshot, screen_ocr as desktop_operator_ocr, mouse_action as desktop_operator_mouse_action, drag_mouse as desktop_operator_drag_mouse, scroll as desktop_operator_scroll, keyboard_action as desktop_operator_keyboard_action, wait as desktop_operator_wait, close_focused_window as desktop_operator_close_focused_window, run_desktop_sequence as desktop_operator_sequence

APP_NAME = "Stella AI Agent"
APP_VERSION = "3.8.0"
DEFAULT_MODEL = os.getenv("STELLA_MODEL", "qwen2.5-coder:3b")
DEFAULT_PROVIDER = os.getenv("STELLA_PROVIDER", "ollama").lower()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("STELLA_OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))

MAX_TOOL_ROUNDS = int(os.getenv("STELLA_MAX_TOOL_ROUNDS", "24"))
MAX_FILE_CHARS = int(os.getenv("STELLA_MAX_FILE_CHARS", "70000"))
MAX_COMMAND_OUTPUT = int(os.getenv("STELLA_MAX_COMMAND_OUTPUT", "50000"))
MAX_CONTEXT_CHARS = int(os.getenv("STELLA_MAX_CONTEXT_CHARS", "180000"))
SESSION_KEEP_MESSAGES = int(os.getenv("STELLA_SESSION_KEEP", "28"))

console = Console()

SYSTEM_PROMPT = """
Ты Stella AI Agent 3.8 — оригинальный терминальный AI-агент с Enterprise Autopilot/Operator-режимом для разработки, исследования, автоматизации, браузерных сценариев, серверов, отчётов и прозрачного журнала действий.

Твоя задача — помогать пользователю как senior-разработчик и аккуратный оператор компьютера: анализировать проект, писать и редактировать код, запускать тесты, работать с Git, искать информацию, открывать браузер/приложения, запускать локальные сервисы и координировать дополнительные агенты.

Важно: ты не являешься Claude Code, Codex, Aider или другой чужой системой. Ты Stella. Не копируй чужой бренд и не утверждай, что являешься продуктом другой компании. Можешь иметь сопоставимые категории возможностей, но действуй как оригинальный продукт.

Протокол инструментов:
- Если нужен инструмент, отвечай ТОЛЬКО строгим JSON без Markdown:
  {"tool":"tool_name","args":{"key":"value"}}
- Если нужно несколько независимых действий, вызывай инструменты по одному.
- Когда задача завершена, отвечай ТОЛЬКО строгим JSON:
  {"final":"ответ пользователю"}

Рабочий стиль:
- Всегда сначала изучай реальные файлы через tree/list_dir/read_file/search_text, если пользователь просит анализ проекта.
- При изменениях кода сначала читай релевантные файлы, затем делай минимальные точные правки, потом запускай проверку/тест.
- Не выдумывай вывод команд, файлов, сайтов или Git-состояния. Для фактов используй инструменты.
- Для команд, которые меняют систему, сеть, зависимости, GitHub, Docker, SSH, браузерные действия или покупки, проси/получай подтверждение через встроенный механизм инструментов.
- Не выполняй скрытое удалённое управление, кражу токенов, обход авторизации, вредоносный код, разрушительные действия, спам или действия без согласия пользователя.
- Если пользователь хочет Telegram/WhatsApp/браузер/покупки/удалённое управление — делай только прозрачный сценарий с явным согласием, логированием, allowlist и подтверждениями опасных операций.

Доступные инструменты:
- list_dir(path=".") — список файлов.
- tree(path=".", depth=3) — дерево проекта.
- find_files(query, path=".") — поиск файлов по имени.
- search_text(pattern, path=".") — regex/текстовый поиск по файлам.
- read_file(path, start_line=1, end_line=0) — чтение файла или диапазона строк.
- write_file(path, content) — создать/перезаписать файл.
- append_file(path, content) — добавить текст.
- edit_file(path, old, new, replace_all=false) — точная замена.
- make_dir(path) — создать папку.
- delete_path(path) — удалить файл/папку с подтверждением.
- run_command(command, reason="", timeout=240) — выполнить shell-команду.
- git_status(), git_diff(path=""), git_log(limit=12), git_commit(message, add_all=false) — Git.
- web_search(query, max_results=8), web_fetch(url) — интернет.
    - open_url(url), open_app(name_or_path, args="") — открыть браузер или приложение с подтверждением.
    - move_mouse(x, y, duration=0.2) — переместить курсор мыши.
    - click(x, y, button=\'left\') — кликнуть мышью.
    - type_text(text, interval=0.01) — ввести текст.
    - press_key(key) — нажать клавишу.
    - hotkey(*args) — нажать комбинацию клавиш.
    - screenshot(filename=\'screenshot.png\') — сделать скриншот экрана.
    - get_screen_resolution() — получить разрешение экрана.
    - phone_devices(), phone_tap(x,y), phone_swipe(x1,y1,x2,y2), phone_text(text), phone_keyevent(keycode), phone_screenshot(filename) — управление Android через adb.
    - pixel_agents_status(), pixel_agents_start(port=4242) — интеграция с pixel-agents companion UI.
    - create_plan(title, steps), update_plan(step_index, status, note="") — рабочий план.
    - spawn_agents(tasks) — запустить несколько мини-агентов Stella последовательно для анализа/идей.
    - autopilot_plan(task, max_agents=12) — построить Operator-план с risk-классификацией и журналом.
    - autopilot_research(query, urls=[], max_results=8) — искать, читать источники и сохранять research_notes.json.
    - github_scan(repo_url, max_files=80) — просканировать публичный GitHub-репозиторий через API без запуска чужого кода.
    - draft_report(recipient, subject, summary, attachments=[], messenger=\'telegram\') — подготовить отчёт/сообщение для начальника или команды.
    - telegram_action(recipient, message, attachments=[]) — подготовить прозрачную отправку через Telegram без скрытой отправки.
    - home_assistant_action(base_url, token_env, domain, service, entity_id, data, dry_run=true) — подготовить или выполнить Home Assistant service call после подтверждения.
    - operator_action(action, details={}, sensitive=true) — зафиксировать и подтвердить чувствительное действие.
    - connector_profile(kind, name, config) — создать профиль сервера/Home Assistant/API без раскрытия секретов.
    - pixel_agents_install(mode=\'prepare\') — скачать/собрать pixel-agents из GitHub после подтверждения.
    - live_actions_viewer() — создать HTML-viewer последних действий Stella.
    - desktop_status() — проверить, доступен ли экран, мышь, окна, OCR и desktop-control зависимости.
    - desktop_windows() — получить список открытых окон.
    - desktop_focus(title_contains='', index=null) — сфокусировать окно по названию или индексу.
    - desktop_running_apps(limit=250), desktop_app_inventory(limit=500) — посмотреть запущенные и установленные приложения.
    - desktop_launch(name_or_path, args='') — запустить приложение через Desktop Operator с подтверждением.
    - desktop_screenshot(filename='desktop_screenshot.png') — сделать скриншот экрана в .stella/screenshots.
    - desktop_ocr(image_path='', lang='eng+rus') — распознать текст с экрана/картинки через Tesseract, если установлен.
    - desktop_mouse(action='click', x=null, y=null, button='left', clicks=1) — move/click/double_click/right_click по координатам.
    - desktop_keyboard(action='press', text='', keys=[]) — type/press/hotkey через клавиатуру.
    - desktop_scroll(clicks=-5, x=null, y=null), desktop_drag(x, y, duration=0.4) — прокрутка и drag-and-drop.
    - desktop_sequence(steps=[], dry_run=true) — выполнить или предварительно показать макро-последовательность desktop-действий.
    - visual_qa(url, filename=\'visual_qa_screenshot.png\', delay=2) — открыть URL в браузере и сделать скриншот.
    - security_scan(url, type='sqli|xss', parameter='id') — проверить URL на уязвимости (SQLi, XSS).

    Autopilot-правило: если задача большая, новая или кажется невозможной, не говори сразу «невозможно». Сначала используй планирование, интернет-исследование, GitHub/source scan, мини-агентов и реальные проверки. Если действие связано с деньгами, аккаунтами, отправкой сообщений, SSH, устройствами, домом или чужими сервисами — подготовь прозрачные шаги, запиши их в журнал и запроси подтверждение перед реальным выполнением.
    Desktop Operator-правило: можешь управлять приложениями и экраном только прозрачно. Сначала получи desktop_status/screenshot/OCR/list_windows, затем действуй маленькими шагами и проверяй результат. Для ввода паролей, платежей, отправки сообщений, удаления файлов, закрытия важных окон, установки ПО, изменения системных настроек и действий в чужих аккаунтах обязательно используй подтверждение; не обходи логин, 2FA, CAPTCHA и запреты пользователя.
""".strip()

ASCII_ART = r"""
   ███████╗████████╗███████╗██╗     ██╗      █████╗        █████╗ ██╗
   ██╔════╝╚══██╔══╝██╔════╝██║     ██║     ██╔══██╗      ██╔══██╗██║
   ███████╗   ██║   █████╗  ██║     ██║     ███████║█████╗███████║██║
   ╚════██║   ██║   ██╔══╝  ██║     ██║     ██╔══██║╚════╝██╔══██║██║
   ███████║   ██║   ███████╗███████╗███████╗██║  ██║      ██║  ██║██║
   ╚══════╝   ╚═╝   ╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝      ╚═╝  ╚═╝╚═╝
""".rstrip()

IGNORED_NAMES = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "__pycache__", "node_modules",
    ".next", ".nuxt", "dist", "build", ".stella", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", "coverage", ".idea", ".vscode", ".DS_Store",
}

DANGEROUS_PATTERNS = [
    r"\brm\s+-[^\n]*[rf][^\n]*\s+(/|\*|\.|~)",
    r"\brm\s+-[^\n]*[rf][^\n]*(--no-preserve-root)",
    r"\bdel\s+(/s|/q|\*)",
    r"\berase\s+(/s|/q|\*)",
    r"\bformat\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bmkfs\b",
    r"\bdd\s+",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-[^\n]*[fdx]",
    r"\bRemove-Item\b.*\s-Recurse\b.*\s-Force\b",
    r"\bchmod\s+777\s+(/|~)",
]

AUTO_SAFE_COMMANDS = {
    "python", "python3", "py", "pytest", "ruff", "mypy", "node", "deno", "bun",
    "dir", "ls", "pwd", "echo", "type", "cat", "find", "findstr", "rg", "grep", "tree",
    "get-childitem", "get-content", "git", "whoami", "hostname", "date",
}

CONFIRM_COMMANDS = {
    "pip", "pip3", "npm", "pnpm", "yarn", "curl", "wget", "ssh", "scp", "rsync",
    "docker", "docker-compose", "gh", "ollama", "powershell", "pwsh", "cmd", "bash", "sh",
    "sudo", "winget", "brew", "apt", "apt-get", "choco", "scoop", "npx",
}

@dataclass
class ToolResult:
    ok: bool
    content: str

@dataclass
class StellaPlan:
    title: str = "Рабочий план"
    steps: list[dict[str, str]] = field(default_factory=list)

class StellaAgent:
    def __init__(self, model: str = DEFAULT_MODEL, provider: str = DEFAULT_PROVIDER, root: Path | None = None, approval_mode: str = "ask") -> None:
        self.model = model
        self.provider = provider
        self.root = (root or Path.cwd()).expanduser().resolve()
        self.approval_mode = normalize_approval_mode(approval_mode)
        self.messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.plan = StellaPlan()
        self.pixel_process: subprocess.Popen[str] | None = None
        self.pixel_session_id = uuid.uuid4().hex
        self.session_file = self._new_session_file()
        self.pixel_session_file = self._new_pixel_session_file()
        self._pending_pixel_tool_id: str | None = None
        self._pixel_hook_cfg: dict[str, Any] | None = None
        self._pixel_hook_disabled = False
        self.status_window = StellaStatusWindow()
        self._log("session_start", {"model": self.model, "provider": self.provider, "root": str(self.root), "version": APP_VERSION, "pixel_jsonl": str(self.pixel_session_file)})
        self._pixel_hook_emit("SessionStart", source="startup", transcript_path=str(self.pixel_session_file), cwd=str(self.root))

    def _new_session_file(self) -> Path:
        session_dir = self.root / ".stella" / "sessions"
        session_dir.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        return session_dir / f"{stamp}.jsonl"

    def _new_pixel_session_file(self) -> Path:
        """Create a Claude-compatible JSONL location so Pixel Agents can visualize Stella sessions.

        Pixel Agents/Claude Code derives the project directory name from cwd by replacing every
        non-alphanumeric character (except '-') with '-'. Using the same algorithm here lets the
        external session scanner adopt Stella's transcript without any extra metadata.
        """
        normalized = re.sub(r"[^A-Za-z0-9-]", "-", str(self.root))
        session_dir = Path.home() / ".claude" / "projects" / normalized
        session_dir.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        return session_dir / f"stella-{stamp}-{self.pixel_session_id[:8]}.jsonl"

    def _log(self, event: str, data: dict[str, Any]) -> None:
        try:
            record = {"time": dt.datetime.now().isoformat(timespec="seconds"), "event": event, "data": data}
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            with self.session_file.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def clear(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._log("context_clear", {})

    def set_model(self, model: str) -> None:
        self.model = model
        self._log("model_change", {"model": model})

    def set_provider(self, provider: str) -> None:
        provider = provider.lower().strip()
        if provider not in {"ollama", "openai"}:
            raise ValueError("Поддерживаются provider: ollama или openai")
        self.provider = provider
        self._log("provider_change", {"provider": provider})

    def set_root(self, root: Path) -> None:
        self.root = root.expanduser().resolve()
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.session_file = self._new_session_file()
        self.pixel_session_id = uuid.uuid4().hex
        self.pixel_session_file = self._new_pixel_session_file()
        self._log("root_change", {"root": str(self.root), "model": self.model, "provider": self.provider, "pixel_jsonl": str(self.pixel_session_file)})
        self._pixel_hook_emit("SessionStart", source="root_change", transcript_path=str(self.pixel_session_file), cwd=str(self.root))

    def chat(self, user_text: str) -> str:
        if looks_like_project_question(user_text):
            snapshot = self.build_project_snapshot()
            user_text = f"{user_text}\n\nРЕАЛЬНЫЙ СНИМОК ПРОЕКТА:\n{snapshot}\n\nОтветь на основе этих данных."
        self._add_message("user", user_text)
        self.status_window.start("Stella AI: Думаю...")
        try:
            for _ in range(MAX_TOOL_ROUNDS):
                self._compact_context_if_needed()
                assistant_text = self._call_model()
                self._add_message("assistant", assistant_text)
                payload = parse_json_object(assistant_text)
                if not payload:
                    if looks_like_false_no_access(assistant_text):
                        snapshot = self.build_project_snapshot()
                        self._add_message("user", "Файлы доступны через инструменты. Вот снимок проекта:\n" + snapshot)
                        continue
                    self._write_pixel_turn_end()
                    return assistant_text.strip()
                if "final" in payload:
                    self._write_pixel_turn_end()
                    return str(payload["final"]).strip()
                tool_name = payload.get("tool")
                args = payload.get("args", {})
                if not isinstance(tool_name, str):
                    return "Модель вернула некорректный вызов инструмента."
                if not isinstance(args, dict):
                    args = {}
                self.status_window.update_message(f"Stella AI: Выполняю {tool_name}...")
                result = self.run_tool(tool_name, args)
                self._print_tool_result(tool_name, args, result)
                self._write_pixel_tool_result(result)
                self._log("tool", {"name": tool_name, "args": redact_secrets(args), "ok": result.ok, "result": result.content[:5000]})
                self._add_message("user", "РЕЗУЛЬТАТ ИНСТРУМЕНТА:\n" + json.dumps({"tool": tool_name, "ok": result.ok, "result": result.content}, ensure_ascii=False))
            return "Я остановилась после лимита инструментов, чтобы не уйти в бесконечный цикл. Напиши `продолжай`, если нужно продолжить."
        finally:
            self.status_window.stop()

    def _add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
        self._log("message", {"role": role, "content": content[:20000]})
        self._write_pixel_message(role, content)

    def _write_pixel_record(self, record: dict[str, Any]) -> None:
        try:
            record.setdefault("sessionId", self.pixel_session_id)
            record.setdefault("cwd", str(self.root))
            record.setdefault("timestamp", dt.datetime.now(dt.timezone.utc).isoformat())
            self.pixel_session_file.parent.mkdir(parents=True, exist_ok=True)
            with self.pixel_session_file.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def _write_pixel_message(self, role: str, content: str) -> None:
        if content.startswith("РЕЗУЛЬТАТ ИНСТРУМЕНТА:"):
            return
        if role == "user":
            self._write_pixel_record({"type": "user", "message": {"role": "user", "content": content}})
            return
        if role != "assistant":
            return
        payload = parse_json_object(content)
        if payload and "tool" in payload:
            tool_id = "toolu_stella_" + uuid.uuid4().hex[:18]
            self._pending_pixel_tool_id = tool_id
            tool_name = str(payload.get("tool"))
            tool_input = payload.get("args", {}) if isinstance(payload.get("args", {}), dict) else {}
            self._write_pixel_record({
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "tool_use", "id": tool_id, "name": tool_name, "input": tool_input}]},
            })
            self._pixel_hook_emit("PreToolUse", tool_name=tool_name, tool_input=tool_input)
        else:
            final_text = str(payload.get("final")) if payload and "final" in payload else content
            self._write_pixel_record({"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": final_text}]}})

    def _write_pixel_tool_result(self, result: ToolResult) -> None:
        tool_id = self._pending_pixel_tool_id
        if not tool_id:
            return
        self._write_pixel_record({
            "type": "user",
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_id, "content": result.content[:12000], "is_error": not result.ok}]},
        })
        self._pixel_hook_emit("PostToolUseFailure" if not result.ok else "PostToolUse")
        self._pending_pixel_tool_id = None

    def _write_pixel_turn_end(self) -> None:
        self._write_pixel_record({"type": "system", "subtype": "turn_duration", "duration_ms": 0})
        self._pixel_hook_emit("Stop")

    def _pixel_hook_config(self) -> dict[str, Any] | None:
        if self._pixel_hook_disabled:
            return None
        if self._pixel_hook_cfg is not None:
            return self._pixel_hook_cfg
        try:
            raw = (Path.home() / ".pixel-agents" / "server.json").read_text(encoding="utf-8")
            cfg = json.loads(raw)
            if isinstance(cfg, dict) and cfg.get("port") and cfg.get("token"):
                self._pixel_hook_cfg = cfg
                return cfg
        except (OSError, ValueError):
            pass
        self._pixel_hook_disabled = True
        return None

    def _pixel_hook_emit(self, hook_event_name: str, **extra: Any) -> None:
        cfg = self._pixel_hook_config()
        if not cfg:
            return
        payload: dict[str, Any] = {
            "session_id": self.pixel_session_id,
            "hook_event_name": hook_event_name,
            "cwd": str(self.root),
            "transcript_path": str(self.pixel_session_file),
        }
        payload.update(extra)
        try:
            requests.post(
                f"http://127.0.0.1:{cfg['port']}/api/hooks/claude",
                json=payload,
                headers={"Authorization": f"Bearer {cfg['token']}"},
                timeout=1.5,
            )
        except (requests.RequestException, OSError):
            pass

    def _compact_context_if_needed(self) -> None:
        total = sum(len(item.get("content", "")) for item in self.messages)
        if total <= MAX_CONTEXT_CHARS or len(self.messages) <= SESSION_KEEP_MESSAGES:
            return
        system = self.messages[:1]
        recent = self.messages[-SESSION_KEEP_MESSAGES:]
        notice = {"role": "user", "content": "Контекст автоматически сжат: старые сообщения опущены, но текущая задача продолжается."}
        self.messages = system + [notice] + recent
        self._log("context_compact", {"kept_messages": len(self.messages)})

    def _call_model(self) -> str:
        if self.provider == "openai":
            return self._call_openai_compatible()
        return self._call_ollama()

    def _call_ollama(self) -> str:
        try:
            with console.status("[bold cyan]Stella думает...[/bold cyan]", spinner="dots12"):
                response = requests.post(
                    f"{OLLAMA_URL}/api/chat",
                    json={"model": self.model, "messages": self.messages, "stream": False, "options": {"temperature": 0.12, "num_ctx": 32768}},
                    timeout=360,
                )
        except requests.ConnectionError as exc:
            raise RuntimeError(f"Ollama не запущена. Запусти `ollama serve`, затем `ollama pull {self.model}`.") from exc
        except requests.Timeout as exc:
            raise RuntimeError("Модель слишком долго не отвечает. Попробуй меньшую модель или повтори запрос.") from exc
        if response.status_code == 404:
            raise RuntimeError(f"Модель `{self.model}` не найдена. Выполни: ollama pull {self.model}")
        if response.status_code >= 400:
            raise RuntimeError(f"Ошибка Ollama {response.status_code}: {response.text[:1000]}")
        data = response.json()
        return data.get("message", {}).get("content", "").strip()

    def _call_openai_compatible(self) -> str:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY не задан. Установи переменную окружения или используй provider ollama.")
        model = self.model if self.model != DEFAULT_MODEL else OPENAI_MODEL
        try:
            with console.status("[bold cyan]Stella думает через OpenAI-compatible API...[/bold cyan]", spinner="dots12"):
                response = requests.post(
                    f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                    json={"model": model, "messages": self.messages, "temperature": 0.12},
                    timeout=360,
                )
        except requests.RequestException as exc:
            raise RuntimeError(f"Ошибка API: {exc}") from exc
        if response.status_code >= 400:
            raise RuntimeError(f"Ошибка API {response.status_code}: {response.text[:1200]}")
        data = response.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

    def run_tool(self, name: str, args: dict[str, Any]) -> ToolResult:
        tools: dict[str, Callable[..., ToolResult]] = {
            "list_dir": self.tool_list_dir,
            "tree": self.tool_tree,
            "find_files": self.tool_find_files,
            "search_text": self.tool_search_text,
            "read_file": self.tool_read_file,
            "write_file": self.tool_write_file,
            "append_file": self.tool_append_file,
            "edit_file": self.tool_edit_file,
            "make_dir": self.tool_make_dir,
            "delete_path": self.tool_delete_path,
            "run_command": self.tool_run_command,
            "git_status": self.tool_git_status,
            "git_diff": self.tool_git_diff,
            "git_log": self.tool_git_log,
            "git_commit": self.tool_git_commit,
            "web_search": self.tool_web_search,
            "web_fetch": self.tool_web_fetch,
            "open_url": self.tool_open_url,
            "open_app": self.tool_open_app,
            "pixel_agents_status": self.tool_pixel_agents_status,
            "pixel_agents_start": self.tool_pixel_agents_start,
            "create_plan": self.tool_create_plan,
            "update_plan": self.tool_update_plan,
            "spawn_agents": self.tool_spawn_agents,
            "move_mouse": self.tool_move_mouse,
            "click": self.tool_click,
            "type_text": self.tool_type_text,
            "press_key": self.tool_press_key,
            "hotkey": self.tool_hotkey,
            "screenshot": self.tool_screenshot,
            "get_screen_resolution": self.tool_get_screen_resolution,
            "phone_devices": self.tool_phone_devices,
            "phone_shell": self.tool_phone_shell,
            "phone_tap": self.tool_phone_tap,
            "phone_swipe": self.tool_phone_swipe,
            "phone_text": self.tool_phone_text,
            "phone_keyevent": self.tool_phone_keyevent,
            "phone_screenshot": self.tool_phone_screenshot,
            "visual_qa": self.tool_visual_qa,
            "security_scan": self.tool_security_scan,
            "ssh_run": self.tool_ssh_run,
            "deploy_app": self.tool_deploy_app,
            "analyze_style": self.tool_analyze_style,
            "bot_sandbox": self.tool_bot_sandbox,
            "autopilot_plan": self.tool_autopilot_plan,
            "autopilot_research": self.tool_autopilot_research,
            "github_scan": self.tool_github_scan,
            "draft_report": self.tool_draft_report,
            "telegram_action": self.tool_telegram_action,
            "home_assistant_action": self.tool_home_assistant_action,
            "operator_action": self.tool_operator_action,
            "connector_profile": self.tool_connector_profile,
            "pixel_agents_install": self.tool_pixel_agents_install,
            "live_actions_viewer": self.tool_live_actions_viewer,
            "desktop_status": self.tool_desktop_status,
            "desktop_windows": self.tool_desktop_windows,
            "desktop_focus": self.tool_desktop_focus,
            "desktop_running_apps": self.tool_desktop_running_apps,
            "desktop_app_inventory": self.tool_desktop_app_inventory,
            "desktop_launch": self.tool_desktop_launch,
            "desktop_screenshot": self.tool_desktop_screenshot,
            "desktop_ocr": self.tool_desktop_ocr,
            "desktop_mouse": self.tool_desktop_mouse,
            "desktop_drag": self.tool_desktop_drag,
            "desktop_scroll": self.tool_desktop_scroll,
            "desktop_keyboard": self.tool_desktop_keyboard,
            "desktop_sequence": self.tool_desktop_sequence,
            "desktop_close_window": self.tool_desktop_close_window,
        }
        fn = tools.get(name)
        if not fn:
            return ToolResult(False, f"Неизвестный инструмент: {name}")
        try:
            return fn(**args)
        except TypeError as exc:
            return ToolResult(False, f"Неверные аргументы инструмента {name}: {exc}")
        except Exception as exc:
            return ToolResult(False, f"{type(exc).__name__}: {exc}")

    def resolve_path(self, user_path: str | None) -> Path:
        raw = (user_path or ".").strip()
        target = (self.root / raw).expanduser().resolve()
        if target != self.root and self.root not in target.parents:
            raise ValueError("Путь находится вне активной папки проекта. Используй /папка или /cd, чтобы сменить корень.")
        return target

    def tool_list_dir(self, path: str = ".") -> ToolResult:
        target = self.resolve_path(path)
        if not target.exists():
            return ToolResult(False, f"Путь не существует: {path}")
        if not target.is_dir():
            return ToolResult(False, f"Это не папка: {path}")
        lines = []
        for item in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            marker = "/" if item.is_dir() else ""
            size = "" if item.is_dir() else f" {human_size(item.stat().st_size)}"
            lines.append(f"{item.relative_to(self.root)}{marker}{size}")
        return ToolResult(True, "\n".join(lines) or "(пусто)")

    def tool_tree(self, path: str = ".", depth: int = 3) -> ToolResult:
        target = self.resolve_path(path)
        if not target.exists() or not target.is_dir():
            return ToolResult(False, f"Папка не существует: {path}")
        depth = max(1, min(int(depth), 8))
        lines = [f"{target.relative_to(self.root) if target != self.root else '.'}/"]
        self._walk_tree(target, lines, "", depth)
        return ToolResult(True, "\n".join(lines))

    def _walk_tree(self, folder: Path, lines: list[str], prefix: str, depth: int) -> None:
        if depth <= 0:
            return
        try:
            items = [p for p in sorted(folder.iterdir(), key=lambda p: (p.is_file(), p.name.lower())) if p.name not in IGNORED_NAMES]
        except OSError:
            return
        clipped = items[:160]
        for index, item in enumerate(clipped):
            branch = "└── " if index == len(clipped) - 1 else "├── "
            lines.append(f"{prefix}{branch}{item.name}{'/' if item.is_dir() else ''}")
            if item.is_dir():
                next_prefix = prefix + ("    " if branch == "└── " else "│   ")
                self._walk_tree(item, lines, next_prefix, depth - 1)
        if len(items) > len(clipped):
            lines.append(f"{prefix}└── ... ещё {len(items) - len(clipped)}")

    def build_project_snapshot(self) -> str:
        tree = self.tool_tree(".", 3).content
        files = []
        for p in self.root.rglob("*"):
            if p.is_file() and not any(part in IGNORED_NAMES for part in p.relative_to(self.root).parts):
                files.append(p)
                if len(files) > 5000:
                    break
        suffix_counts: dict[str, int] = {}
        for path in files:
            suffix = path.suffix.lower() or "(без расширения)"
            suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1
        important_names = {"README.md", "readme.md", "package.json", "pyproject.toml", "requirements.txt", "Dockerfile", "docker-compose.yml", "compose.yml", "vite.config.ts", "vite.config.js", "next.config.js", "next.config.ts", "tsconfig.json", "main.py", "app.py", "manage.py", "Cargo.toml", "go.mod"}
        previews = []
        for path in [p for p in files if p.name in important_names][:14]:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")[:3500]
            except OSError:
                continue
            previews.append(f"--- {path.relative_to(self.root)} ---\n{text}")
        top_ext = sorted(suffix_counts.items(), key=lambda item: item[1], reverse=True)[:14]
        git = self.tool_git_status().content if (self.root / ".git").exists() else "Git-репозиторий не обнаружен."
        return "\n".join([
            f"Папка проекта: {self.root}",
            f"Файлов найдено: {len(files)}",
            "Основные расширения: " + (", ".join(f"{ext}: {count}" for ext, count in top_ext) if top_ext else "нет файлов"),
            "", "Git:", git[:3000], "", "Дерево проекта:", tree, "", "Важные файлы:", "\n\n".join(previews) if previews else "(нет превью)",
        ])

    def tool_find_files(self, query: str, path: str = ".") -> ToolResult:
        target = self.resolve_path(path)
        if not target.exists() or not target.is_dir():
            return ToolResult(False, f"Папка не существует: {path}")
        query_lower = query.lower()
        matches = []
        for item in target.rglob("*"):
            if any(part in IGNORED_NAMES for part in item.relative_to(self.root).parts):
                continue
            if query_lower in item.name.lower():
                matches.append(str(item.relative_to(self.root)))
            if len(matches) >= 300:
                break
        return ToolResult(True, "\n".join(matches) or "(ничего не найдено)")

    def tool_search_text(self, pattern: str, path: str = ".") -> ToolResult:
        target = self.resolve_path(path)
        if not target.exists():
            return ToolResult(False, f"Путь не существует: {path}")
        try:
            regex = re.compile(pattern, flags=re.IGNORECASE)
        except re.error:
            regex = re.compile(re.escape(pattern), flags=re.IGNORECASE)
        files = [target] if target.is_file() else [p for p in target.rglob("*") if p.is_file()]
        hits = []
        for file_path in files:
            rel_parts = file_path.relative_to(self.root).parts
            if any(part in IGNORED_NAMES for part in rel_parts):
                continue
            try:
                if file_path.stat().st_size > 2_000_000:
                    continue
                text = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for line_no, line in enumerate(text.splitlines(), start=1):
                if regex.search(line):
                    hits.append(f"{file_path.relative_to(self.root)}:{line_no}: {line[:260]}")
                    if len(hits) >= 300:
                        return ToolResult(True, "\n".join(hits))
        return ToolResult(True, "\n".join(hits) or "(ничего не найдено)")

    def tool_read_file(self, path: str, start_line: int = 1, end_line: int = 0) -> ToolResult:
        target = self.resolve_path(path)
        if not target.exists():
            return ToolResult(False, f"Файл не существует: {path}")
        if not target.is_file():
            return ToolResult(False, f"Это не файл: {path}")
        text = target.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        if start_line > 1 or end_line > 0:
            start = max(1, int(start_line))
            end = int(end_line) if int(end_line) > 0 else len(lines)
            selected = lines[start - 1:end]
            text = "\n".join(f"{i}: {line}" for i, line in enumerate(selected, start=start))
        if len(text) > MAX_FILE_CHARS:
            text = text[:MAX_FILE_CHARS] + "\n\n[обрезано]"
        return ToolResult(True, text)

    def tool_write_file(self, path: str, content: str) -> ToolResult:
        target = self.resolve_path(path)
        if target.exists() and not self._approve(f"Перезаписать существующий файл `{target.relative_to(self.root)}`?", risky=False):
            return ToolResult(False, "Пользователь отказался от перезаписи.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolResult(True, f"Записано: {target.relative_to(self.root)} ({len(content)} символов)")

    def tool_append_file(self, path: str, content: str) -> ToolResult:
        target = self.resolve_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(content)
        return ToolResult(True, f"Добавлено: {target.relative_to(self.root)} ({len(content)} символов)")

    def tool_edit_file(self, path: str, old: str, new: str, replace_all: bool = False) -> ToolResult:
        target = self.resolve_path(path)
        if not target.exists() or not target.is_file():
            return ToolResult(False, f"Файл не существует: {path}")
        text = target.read_text(encoding="utf-8", errors="replace")
        if old not in text:
            return ToolResult(False, "Точный фрагмент для замены не найден.")
        count = text.count(old) if replace_all else 1
        target.write_text(text.replace(old, new, 0 if replace_all else 1), encoding="utf-8")
        return ToolResult(True, f"Изменено: {target.relative_to(self.root)}; замен: {count}")

    def tool_make_dir(self, path: str) -> ToolResult:
        target = self.resolve_path(path)
        target.mkdir(parents=True, exist_ok=True)
        return ToolResult(True, f"Папка готова: {target.relative_to(self.root)}")

    def tool_delete_path(self, path: str) -> ToolResult:
        target = self.resolve_path(path)
        if not target.exists():
            return ToolResult(False, f"Путь не существует: {path}")
        rel = target.relative_to(self.root)
        if not self._approve(f"Удалить `{rel}`?", risky=True):
            return ToolResult(False, "Пользователь отказался от удаления.")
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        return ToolResult(True, f"Удалено: {rel}")

    def tool_run_command(self, command: str, reason: str = "", timeout: int = 240) -> ToolResult:
        risk = classify_command(command)
        if risk == "blocked":
            return ToolResult(False, "Команда заблокирована: она выглядит разрушительной. Если это реально нужно, сделай вручную и осознанно.")
        if risk == "confirm":
            console.print(Panel(f"{command}\n\nПричина: {reason or '(не указана)'}", title="Подтверждение команды", border_style="yellow", box=box.ROUNDED))
            if not self._approve("Разрешить Stella выполнить эту команду?", risky=True):
                return ToolResult(False, "Пользователь отказался выполнить команду.")
        completed = subprocess.run(command, cwd=self.root, shell=True, text=True, capture_output=True, timeout=max(5, min(int(timeout), 1800)))
        output = (completed.stdout or "") + (("\n[stderr]\n" + completed.stderr) if completed.stderr else "")
        output = output.strip() or "(нет вывода)"
        if len(output) > MAX_COMMAND_OUTPUT:
            output = output[:MAX_COMMAND_OUTPUT] + "\n\n[обрезано]"
        return ToolResult(completed.returncode == 0, f"exit_code={completed.returncode}\n{output}")

    def tool_git_status(self) -> ToolResult:
        return self._git("git status --short --branch")

    def tool_git_diff(self, path: str = "") -> ToolResult:
        command = "git diff -- " + shlex.quote(path) if path else "git diff"
        return self._git(command)

    def tool_git_log(self, limit: int = 12) -> ToolResult:
        limit = max(1, min(int(limit), 50))
        return self._git(f"git log --oneline --decorate -n {limit}")

    def tool_git_commit(self, message: str, add_all: bool = False) -> ToolResult:
        if not message.strip():
            return ToolResult(False, "Сообщение коммита пустое.")
        if not self._approve(f"Создать Git-коммит: {message!r}?", risky=True):
            return ToolResult(False, "Пользователь отказался от коммита.")
        if add_all:
            add = subprocess.run("git add -A", cwd=self.root, shell=True, text=True, capture_output=True, timeout=120)
            if add.returncode != 0:
                return ToolResult(False, add.stderr or add.stdout or "git add failed")
        return self._git("git commit -m " + shlex.quote(message))

    def _git(self, command: str) -> ToolResult:
        if not (self.root / ".git").exists():
            probe = subprocess.run("git rev-parse --show-toplevel", cwd=self.root, shell=True, text=True, capture_output=True, timeout=20)
            if probe.returncode != 0:
                return ToolResult(False, "Это не Git-репозиторий.")
        return self.tool_run_command(command, reason="Git workflow", timeout=180)

    def tool_web_search(self, query: str, max_results: int = 8) -> ToolResult:
        max_results = max(1, min(int(max_results), 12))
        url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
        response = requests.get(url, timeout=35, headers={"User-Agent": "Mozilla/5.0 Stella-AI-Agent/3.8"})
        response.raise_for_status()
        blocks = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', response.text, re.I | re.S)
        results = []
        for raw_href, raw_title in blocks:
            href = html_lib.unescape(raw_href)
            parsed = urllib.parse.urlparse(href)
            params = urllib.parse.parse_qs(parsed.query)
            if "uddg" in params:
                href = params["uddg"][0]
            title = strip_html(raw_title)
            if title and href:
                results.append(f"- {title}\n  {href}")
            if len(results) >= max_results:
                break
        return ToolResult(bool(results), "\n".join(results) if results else "Ничего не найдено.")

    def tool_web_fetch(self, url: str) -> ToolResult:
        if not re.match(r"^https?://", url):
            return ToolResult(False, "Поддерживаются только http:// и https://.")
        response = requests.get(url, timeout=45, headers={"User-Agent": "Mozilla/5.0 Stella-AI-Agent/3.8"})
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        text = response.text
        if "html" in content_type.lower():
            text = html_to_text(text)
        if len(text) > MAX_FILE_CHARS:
            text = text[:MAX_FILE_CHARS] + "\n\n[обрезано]"
        return ToolResult(True, text)

    def tool_open_url(self, url: str) -> ToolResult:
        if not re.match(r"^https?://", url):
            return ToolResult(False, "Поддерживаются только http:// и https://.")
        if not self._approve(f"Открыть в браузере: {url}?", risky=True):
            return ToolResult(False, "Пользователь отказался открыть браузер.")
        opened = webbrowser.open(url)
        return ToolResult(opened, "Браузер открыт." if opened else "Не удалось открыть браузер.")

    def tool_open_app(self, name_or_path: str, args: str = "") -> ToolResult:
        if not name_or_path.strip():
            return ToolResult(False, "Не указано приложение.")
        if not self._approve(f"Открыть приложение/команду: {name_or_path} {args}?", risky=True):
            return ToolResult(False, "Пользователь отказался открыть приложение.")
        system = platform.system().lower()
        if system == "windows":
            cmd = f'start "" {shlex.quote(name_or_path)} {args}'
        elif system == "darwin":
            cmd = f'open {shlex.quote(name_or_path)} --args {args}' if Path(name_or_path).exists() else f'open -a {shlex.quote(name_or_path)} --args {args}'
        else:
            cmd = f"{shlex.quote(name_or_path)} {args}"
        try:
            subprocess.Popen(cmd, cwd=self.root, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return ToolResult(True, f"Запущено: {name_or_path}")
        except Exception as exc:
            return ToolResult(False, f"Не удалось запустить: {exc}")


    def _legacy_gui_json(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> ToolResult:
        try:
            data = fn(*args, **kwargs)
            return ToolResult(bool(data.get("ok", True)) if isinstance(data, dict) else True, json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as exc:
            return ToolResult(False, f"GUI tool error: {type(exc).__name__}: {exc}")

    def tool_move_mouse(self, x: int, y: int, duration: float = 0.2) -> ToolResult:
        if not self._approve(f"Переместить мышь в x={x}, y={y}?", risky=True):
            return ToolResult(False, "Пользователь отказался перемещать мышь.")
        return self._legacy_gui_json(move_mouse, int(x), int(y), float(duration))

    def tool_click(self, x: int, y: int, button: str = "left") -> ToolResult:
        if not self._approve(f"Кликнуть мышью в x={x}, y={y}, button={button}?", risky=True):
            return ToolResult(False, "Пользователь отказался выполнять клик.")
        return self._legacy_gui_json(click, int(x), int(y), button)

    def tool_type_text(self, text: str, interval: float = 0.01) -> ToolResult:
        preview = text[:80] + ("..." if len(text) > 80 else "")
        if not self._approve(f"Ввести текст через GUI: {preview!r}?", risky=True):
            return ToolResult(False, "Пользователь отказался вводить текст.")
        return self._legacy_gui_json(type_text, text, float(interval))

    def tool_press_key(self, key: str) -> ToolResult:
        if not self._approve(f"Нажать клавишу: {key}?", risky=True):
            return ToolResult(False, "Пользователь отказался нажимать клавишу.")
        return self._legacy_gui_json(press_key, key)

    def tool_hotkey(self, keys: list[str] | str) -> ToolResult:
        if isinstance(keys, str):
            key_list = [k.strip() for k in keys.replace("+", ",").split(",") if k.strip()]
        else:
            key_list = [str(k) for k in keys]
        if not key_list:
            return ToolResult(False, "keys должен быть непустым списком или строкой.")
        if not self._approve(f"Нажать горячую клавишу: {'+'.join(key_list)}?", risky=True):
            return ToolResult(False, "Пользователь отказался нажимать hotkey.")
        return self._legacy_gui_json(hotkey, *key_list)

    def tool_screenshot(self, filename: str = "screenshot.png") -> ToolResult:
        target = self.root / ".stella" / "screenshots" / Path(filename).name
        return self._legacy_gui_json(screenshot, str(target))

    def tool_get_screen_resolution(self) -> ToolResult:
        try:
            width, height = get_screen_resolution()
            return ToolResult(True, json.dumps({"ok": True, "width": width, "height": height}, ensure_ascii=False, indent=2))
        except Exception as exc:
            return ToolResult(False, f"GUI tool error: {type(exc).__name__}: {exc}")

    def _desktop_json(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> ToolResult:
        try:
            data = fn(*args, **kwargs)
            return ToolResult(bool(data.get("ok", True)) if isinstance(data, dict) else True, json.dumps(data, ensure_ascii=False, indent=2))
        except Exception as exc:
            return ToolResult(False, f"Desktop Operator error: {type(exc).__name__}: {exc}")

    def tool_desktop_status(self) -> ToolResult:
        return self._desktop_json(desktop_operator_status, self.root)

    def tool_desktop_windows(self) -> ToolResult:
        return self._desktop_json(desktop_operator_list_windows, self.root)

    def tool_desktop_focus(self, title_contains: str = "", index: int | None = None) -> ToolResult:
        if not self._approve(f"Сфокусировать окно `{title_contains or index}`?", risky=True):
            return ToolResult(False, "Пользователь отказался фокусировать окно.")
        return self._desktop_json(desktop_operator_focus_window, self.root, title_contains=title_contains, index=index)

    def tool_desktop_running_apps(self, limit: int = 250) -> ToolResult:
        return self._desktop_json(desktop_operator_running_apps, self.root, limit=limit)

    def tool_desktop_app_inventory(self, limit: int = 500) -> ToolResult:
        return self._desktop_json(desktop_operator_app_inventory, self.root, limit=limit)

    def tool_desktop_launch(self, name_or_path: str, args: str = "") -> ToolResult:
        if not self._approve(f"Запустить приложение через Desktop Operator: {name_or_path} {args}?", risky=True):
            return ToolResult(False, "Пользователь отказался запускать приложение.")
        return self._desktop_json(desktop_operator_launch_app, self.root, name_or_path=name_or_path, args=args)

    def tool_desktop_screenshot(self, filename: str = "desktop_screenshot.png") -> ToolResult:
        return self._desktop_json(desktop_operator_screenshot, self.root, filename=filename)

    def tool_desktop_ocr(self, image_path: str = "", lang: str = "eng+rus") -> ToolResult:
        return self._desktop_json(desktop_operator_ocr, self.root, image_path=image_path, lang=lang)

    def tool_desktop_mouse(self, action: str = "click", x: int | None = None, y: int | None = None, button: str = "left", clicks: int = 1, duration: float = 0.15) -> ToolResult:
        if not self._approve(f"Выполнить действие мышью: {action} x={x} y={y} button={button}?", risky=True):
            return ToolResult(False, "Пользователь отказался выполнять действие мышью.")
        return self._desktop_json(desktop_operator_mouse_action, self.root, action=action, x=x, y=y, button=button, clicks=clicks, duration=duration)

    def tool_desktop_drag(self, x: int, y: int, duration: float = 0.4, button: str = "left") -> ToolResult:
        if not self._approve(f"Выполнить drag-and-drop до x={x} y={y}?", risky=True):
            return ToolResult(False, "Пользователь отказался выполнять drag-and-drop.")
        return self._desktop_json(desktop_operator_drag_mouse, self.root, x=x, y=y, duration=duration, button=button)

    def tool_desktop_scroll(self, clicks: int = -5, x: int | None = None, y: int | None = None) -> ToolResult:
        return self._desktop_json(desktop_operator_scroll, self.root, clicks=clicks, x=x, y=y)

    def tool_desktop_keyboard(self, action: str = "press", text: str = "", keys: list[str] | str | None = None, interval: float = 0.01) -> ToolResult:
        sensitive = action == "type" and any(word in text.lower() for word in ["password", "парол", "token", "secret", "api_key", "карта", "card"])
        if sensitive or action in {"type", "hotkey"}:
            preview = text[:80] + ("..." if len(text) > 80 else "")
            if not self._approve(f"Выполнить клавиатурное действие `{action}` keys={keys} text_preview={preview!r}?", risky=True):
                return ToolResult(False, "Пользователь отказался выполнять клавиатурное действие.")
        return self._desktop_json(desktop_operator_keyboard_action, self.root, action=action, text=text, keys=keys, interval=interval)

    def tool_desktop_sequence(self, steps: list[dict[str, Any]] | str | None = None, dry_run: bool = True) -> ToolResult:
        if not dry_run and not self._approve("Выполнить desktop_sequence на реальном экране?", risky=True):
            return ToolResult(False, "Пользователь отказался выполнять desktop_sequence.")
        return self._desktop_json(desktop_operator_sequence, self.root, steps=steps, dry_run=dry_run)

    def tool_desktop_close_window(self) -> ToolResult:
        if not self._approve("Закрыть активное окно?", risky=True):
            return ToolResult(False, "Пользователь отказался закрывать активное окно.")
        return self._desktop_json(desktop_operator_close_focused_window, self.root)

    def tool_pixel_agents_status(self) -> ToolResult:
        discovery = Path.home() / ".pixel-agents" / "server.json"
        lines = ["Pixel Agents integration status"]
        lines.append("Stella writes a Pixel/Claude-compatible JSONL transcript for visualization and Autopilot operator logs.")
        lines.append(f"Stella Pixel JSONL: {self.pixel_session_file}")
        lines.append(f"Operator JSONL: {self.root / '.stella' / 'operator_actions.jsonl'}")
        lines.append(f"Live viewer: {self.root / '.stella' / 'live_actions.html'}")
        lines.append(f"VS Code: {shutil.which('code') or 'не найден'}")
        lines.append(f"npx: {shutil.which('npx') or 'не найден'}")
        if discovery.exists():
            try:
                lines.append("server.json: " + discovery.read_text(encoding="utf-8")[:2000])
            except OSError as exc:
                lines.append(f"server.json: ошибка чтения {exc}")
        else:
            lines.append("server.json: не найден; companion-сервер, вероятно, не запущен")
        return ToolResult(True, "\n".join(lines))

    def tool_pixel_agents_start(self, port: int = 4242) -> ToolResult:
        message = (
            "Stella пишет совместимый JSONL-журнал для Pixel Agents и Autopilot operator log.\n"
            f"JSONL Stella: {self.pixel_session_file}\n"
            f"Live viewer: {self.root / '.stella' / 'live_actions.html'}\n\n"
            "Поддерживаются два сценария: VS Code extension (рекомендовано README Pixel Agents) "
            "и сборка исходников из https://github.com/pixel-agents-hq/pixel-agents для разработки/standalone-экспериментов."
        )
        actions: list[str] = []
        if shutil.which("code") and self._approve("Открыть текущий проект в VS Code для Pixel Agents?", risky=True):
            subprocess.Popen(["code", str(self.root)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            actions.append("VS Code открыт.")
        if shutil.which("git") and shutil.which("npm") and self._approve("Клонировать/обновить и собрать Pixel Agents из GitHub в ~/.stella-ai-coder/pixel-agents?", risky=True):
            pixel_dir = Path.home() / ".stella-ai-coder" / "pixel-agents"
            pixel_dir.parent.mkdir(parents=True, exist_ok=True)
            if (pixel_dir / ".git").exists():
                subprocess.run(["git", "pull", "--ff-only"], cwd=pixel_dir, text=True, capture_output=True, timeout=120)
            else:
                subprocess.run(["git", "clone", "https://github.com/pixel-agents-hq/pixel-agents.git", str(pixel_dir)], text=True, capture_output=True, timeout=240)
            steps = [
                (["npm", "install"], pixel_dir),
                (["npm", "install"], pixel_dir / "webview-ui"),
                (["npm", "run", "build"], pixel_dir),
            ]
            logs = []
            for cmd, cwd in steps:
                if not cwd.exists():
                    logs.append(f"skip {' '.join(cmd)}: {cwd} не существует")
                    continue
                completed = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=600)
                logs.append(f"$ {' '.join(cmd)} (cwd={cwd}) exit={completed.returncode}\n{(completed.stdout + completed.stderr)[-3000:]}")
                if completed.returncode != 0:
                    break
            actions.append("Pixel Agents source path: " + str(pixel_dir) + "\n" + "\n".join(logs))
        if not actions:
            actions.append("Ничего не запускалось. Можно установить VS Code extension: https://marketplace.visualstudio.com/items?itemName=pablodelucca.pixel-agents")
        return ToolResult(True, message + "\n\n" + "\n\n".join(actions))

    def tool_create_plan(self, title: str, steps: list[str]) -> ToolResult:
        if not isinstance(steps, list) or not steps:
            return ToolResult(False, "steps должен быть непустым списком строк.")
        self.plan = StellaPlan(title=title or "Рабочий план", steps=[{"status": "todo", "text": str(step), "note": ""} for step in steps])
        return ToolResult(True, self._render_plan_text())

    def tool_update_plan(self, step_index: int, status: str, note: str = "") -> ToolResult:
        index = int(step_index) - 1
        if index < 0 or index >= len(self.plan.steps):
            return ToolResult(False, "Нет такого шага плана.")
        if status not in {"todo", "doing", "done", "blocked"}:
            return ToolResult(False, "status должен быть: todo, doing, done, blocked.")
        self.plan.steps[index]["status"] = status
        self.plan.steps[index]["note"] = note
        return ToolResult(True, self._render_plan_text())

    def _render_plan_text(self) -> str:
        lines = [self.plan.title]
        for i, step in enumerate(self.plan.steps, start=1):
            note = f" — {step['note']}" if step.get("note") else ""
            lines.append(f"{i}. [{step['status']}] {step['text']}{note}")
        return "\n".join(lines)









    def tool_bot_sandbox(self, platform: str = "telegram", scenario: dict[str, Any] | str | None = None, handler: str = "", webhook_url: str = "", users: int = 0, messages_per_user: int = 5, concurrency: int = 20) -> ToolResult:
        """Run a local messenger-bot simulation without real Telegram/WhatsApp APIs."""
        platform = (platform or "telegram").lower().strip()
        if platform not in {"telegram", "whatsapp"}:
            return ToolResult(False, "platform должен быть telegram или whatsapp.")
        if isinstance(scenario, str) and scenario.strip():
            try:
                scenario_obj = json.loads(scenario)
            except json.JSONDecodeError as exc:
                return ToolResult(False, f"scenario должен быть JSON: {exc}")
        elif isinstance(scenario, dict):
            scenario_obj = scenario
        else:
            scenario_obj = {"dialogs": [{"chat_id": "1", "text": "/start"}, {"chat_id": "1", "text": "help"}]}
        if webhook_url and not self._approve(f"Отправить sandbox-сообщения на webhook {webhook_url}?", risky=True):
            return ToolResult(False, "Пользователь отказался отправлять запросы на webhook.")
        transcript = self.root / ".stella" / "bot_sandbox_transcript.jsonl"
        sandbox = BotSandbox(platform=platform, transcript_path=transcript)
        loaded_handler = None
        if handler:
            sys.path.insert(0, str(self.root))
            try:
                loaded_handler = load_handler(handler)
            except Exception as exc:
                return ToolResult(False, f"Не удалось загрузить handler {handler}: {exc}")
        try:
            import asyncio
            if users and int(users) > 0:
                result = asyncio.run(sandbox.run_load_test(handler=loaded_handler, webhook_url=webhook_url or None, users=min(int(users), 1000), messages_per_user=max(1, min(int(messages_per_user), 100)), concurrency=max(1, min(int(concurrency), 200))))
            else:
                result = asyncio.run(sandbox.run_script(scenario_obj, handler=loaded_handler, webhook_url=webhook_url or None))
        except Exception as exc:
            return ToolResult(False, f"Ошибка Bot Sandbox: {type(exc).__name__}: {exc}")
        return ToolResult(True, json.dumps(result, ensure_ascii=False, indent=2))

    def tool_ssh_run(self, host: str, user: str, command: str, port: int = 22, identity_file: str = "", timeout: int = 300) -> ToolResult:
        """Run one command on a remote server through the system ssh client.

        Stella intentionally uses the user's local SSH configuration/keys instead of accepting
        passwords or secrets in chat. Every remote command is treated as risky and requires
        confirmation unless approval mode is auto.
        """
        host = str(host or "").strip()
        user = str(user or "").strip()
        command = str(command or "").strip()
        if not host or not user or not command:
            return ToolResult(False, "Нужны host, user и command.")
        if not re.match(r"^[A-Za-z0-9_.:-]+$", host):
            return ToolResult(False, "host содержит недопустимые символы.")
        if not re.match(r"^[A-Za-z0-9_.-]+$", user):
            return ToolResult(False, "user содержит недопустимые символы.")
        try:
            port = max(1, min(int(port), 65535))
            timeout = max(5, min(int(timeout), 1800))
        except (TypeError, ValueError):
            return ToolResult(False, "port/timeout должны быть числами.")
        if not shutil.which("ssh"):
            return ToolResult(False, "ssh-клиент не найден в PATH.")
        if classify_command(command) == "blocked":
            return ToolResult(False, "Удалённая команда выглядит разрушительной и заблокирована.")
        target = f"{user}@{host}"
        if not self._approve(f"Выполнить на удалённом сервере {target}:{port}: {command}?", risky=True):
            return ToolResult(False, "Пользователь отказался выполнять SSH-команду.")
        ssh_cmd = ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new", "-p", str(port)]
        if identity_file:
            key_path = str(Path(identity_file).expanduser())
            ssh_cmd.extend(["-i", key_path])
        ssh_cmd.extend([target, command])
        completed = subprocess.run(ssh_cmd, cwd=self.root, text=True, capture_output=True, timeout=timeout)
        output = (completed.stdout or "") + (completed.stderr or "")
        output = output[:MAX_COMMAND_OUTPUT]
        return ToolResult(completed.returncode == 0, f"exit={completed.returncode}\n{output}".strip())

    def tool_deploy_app(self, config: dict[str, Any] | str) -> ToolResult:
        """Create Docker/Nginx deployment assets and optionally run a VPS deploy via SSH.

        Expected config keys: app_name, domain, port, repo_url, branch, host, user,
        ssh_port, identity_file, project_path, setup_nginx, dockerfile, compose_file.
        Without host/user this tool works in local packaging mode and only writes templates.
        """
        if isinstance(config, str):
            try:
                config = json.loads(config)
            except json.JSONDecodeError as exc:
                return ToolResult(False, f"config должен быть JSON-объектом: {exc}")
        if not isinstance(config, dict):
            return ToolResult(False, "config должен быть dict/JSON-объектом.")
        app_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(config.get("app_name") or self.root.name or "stella-app")).strip("-.") or "stella-app"
        domain = str(config.get("domain") or "example.com").strip()
        app_port = int(config.get("port") or 3000)
        deploy_dir = self.root / ".stella" / "deploy" / app_name
        deploy_dir.mkdir(parents=True, exist_ok=True)
        dockerfile_name = str(config.get("dockerfile") or "Dockerfile")
        compose_file = str(config.get("compose_file") or "docker-compose.yml")
        dockerfile_path = deploy_dir / dockerfile_name
        compose_path = deploy_dir / compose_file
        nginx_path = deploy_dir / "nginx.conf"
        deploy_script_path = deploy_dir / "deploy_remote.sh"

        if not (self.root / dockerfile_name).exists():
            dockerfile_path.write_text("""# Generated by Stella AI Agent 3.8 Enterprise Autopilot\nFROM node:22-alpine AS deps\nWORKDIR /app\nCOPY package*.json pnpm-lock.yaml* yarn.lock* ./\nRUN if [ -f pnpm-lock.yaml ]; then corepack enable && pnpm install --frozen-lockfile; elif [ -f yarn.lock ]; then yarn install --frozen-lockfile; elif [ -f package.json ]; then npm install; else echo 'No Node manifest found'; fi\n\nFROM node:22-alpine\nWORKDIR /app\nENV NODE_ENV=production\nCOPY --from=deps /app/node_modules ./node_modules\nCOPY . .\nRUN if [ -f package.json ]; then npm run build --if-present; fi\nEXPOSE 3000\nCMD if [ -f package.json ]; then npm run start --if-present || npm run preview -- --host 0.0.0.0; else python3 -m http.server 3000; fi\n""", encoding="utf-8")
        compose_path.write_text(f"""services:\n  {app_name}:\n    build:\n      context: .\n      dockerfile: {dockerfile_name}\n    container_name: {app_name}\n    restart: unless-stopped\n    ports:\n      - \"127.0.0.1:{app_port}:3000\"\n    environment:\n      NODE_ENV: production\n""", encoding="utf-8")
        nginx_path.write_text(f"""server {{\n    listen 80;\n    server_name {domain};\n\n    location / {{\n        proxy_pass http://127.0.0.1:{app_port};\n        proxy_http_version 1.1;\n        proxy_set_header Upgrade $http_upgrade;\n        proxy_set_header Connection 'upgrade';\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n        proxy_cache_bypass $http_upgrade;\n    }}\n}}\n""", encoding="utf-8")

        repo_url = str(config.get("repo_url") or "").strip()
        branch = str(config.get("branch") or "main").strip()
        project_path = str(config.get("project_path") or f"/opt/{app_name}").strip()
        setup_nginx = bool(config.get("setup_nginx", True))
        remote_script = self._build_remote_deploy_script(app_name, repo_url, branch, project_path, domain, app_port, setup_nginx)
        deploy_script_path.write_text(remote_script, encoding="utf-8")
        try:
            deploy_script_path.chmod(0o755)
        except OSError:
            pass

        host = str(config.get("host") or "").strip()
        user = str(config.get("user") or "").strip()
        if not host or not user:
            return ToolResult(True, "Deployment-kit создан локально. Для реального деплоя передай host/user/repo_url.\n" + "\n".join(str(p.relative_to(self.root)) for p in [dockerfile_path, compose_path, nginx_path, deploy_script_path] if p.exists()))
        if not repo_url:
            return ToolResult(False, "Для удалённого deploy_app нужен repo_url, чтобы сервер мог получить код через git.")
        if not self._approve(f"Развернуть {app_name} на {user}@{host} в {project_path}?", risky=True):
            return ToolResult(False, "Пользователь отказался от деплоя.")
        quoted_script = shlex.quote(remote_script)
        remote_cmd = f"bash -lc {quoted_script}"
        return self.tool_ssh_run(host=host, user=user, command=remote_cmd, port=int(config.get("ssh_port") or 22), identity_file=str(config.get("identity_file") or ""), timeout=int(config.get("timeout") or 900))

    def _build_remote_deploy_script(self, app_name: str, repo_url: str, branch: str, project_path: str, domain: str, app_port: int, setup_nginx: bool) -> str:
        nginx_block = f"""cat > /etc/nginx/sites-available/{app_name} <<'NGINX'\nserver {{\n    listen 80;\n    server_name {domain};\n    location / {{\n        proxy_pass http://127.0.0.1:{app_port};\n        proxy_http_version 1.1;\n        proxy_set_header Upgrade $http_upgrade;\n        proxy_set_header Connection 'upgrade';\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n        proxy_cache_bypass $http_upgrade;\n    }}\n}}\nNGINX\nln -sf /etc/nginx/sites-available/{app_name} /etc/nginx/sites-enabled/{app_name}\nnginx -t && systemctl reload nginx\n""" if setup_nginx else "echo 'Nginx setup skipped'\n"
        return f"""set -euo pipefail\nAPP_NAME={shlex.quote(app_name)}\nREPO_URL={shlex.quote(repo_url)}\nBRANCH={shlex.quote(branch)}\nPROJECT_PATH={shlex.quote(project_path)}\n\nexport DEBIAN_FRONTEND=noninteractive\nif command -v apt-get >/dev/null 2>&1; then\n  apt-get update -y\n  apt-get install -y git curl ca-certificates nginx docker.io docker-compose-plugin\nfi\nsystemctl enable --now docker || true\nmkdir -p \"$(dirname \"$PROJECT_PATH\")\"\nif [ -d \"$PROJECT_PATH/.git\" ]; then\n  git -C \"$PROJECT_PATH\" fetch origin \"$BRANCH\"\n  git -C \"$PROJECT_PATH\" checkout \"$BRANCH\"\n  git -C \"$PROJECT_PATH\" pull --ff-only origin \"$BRANCH\"\nelse\n  rm -rf \"$PROJECT_PATH\"\n  git clone --branch \"$BRANCH\" \"$REPO_URL\" \"$PROJECT_PATH\"\nfi\ncd \"$PROJECT_PATH\"\nif [ ! -f Dockerfile ]; then\ncat > Dockerfile <<'DOCKERFILE'\nFROM node:22-alpine\nWORKDIR /app\nCOPY . .\nRUN if [ -f package.json ]; then corepack enable || true; npm install; npm run build --if-present; fi\nEXPOSE 3000\nCMD if [ -f package.json ]; then npm run start --if-present || npm run preview -- --host 0.0.0.0; else python3 -m http.server 3000; fi\nDOCKERFILE\nfi\ncat > docker-compose.yml <<'COMPOSE'\nservices:\n  app:\n    build: .\n    restart: unless-stopped\n    ports:\n      - \"127.0.0.1:{app_port}:3000\"\n    environment:\n      NODE_ENV: production\nCOMPOSE\ndocker compose up -d --build\n{nginx_block}\necho \"Deployment completed for $APP_NAME\"\n"""

    def tool_analyze_style(self, path: str = ".") -> ToolResult:
        target = self.resolve_path(path)
        if not target.exists() or not target.is_dir():
            return ToolResult(False, f"Папка не существует: {path}")
        candidates = [".editorconfig", ".eslintrc", ".eslintrc.json", ".eslintrc.js", ".prettierrc", ".prettierrc.json", "pyproject.toml", "setup.cfg", "ruff.toml", "package.json"]
        sections: list[str] = []
        for name in candidates:
            file_path = target / name
            if file_path.exists() and file_path.is_file():
                try:
                    sections.append(f"## {name}\n```\n{file_path.read_text(encoding='utf-8', errors='replace')[:6000]}\n```")
                except OSError:
                    pass
        git_summary = ""
        if (target / ".git").exists() or (self.root / ".git").exists():
            try:
                log = subprocess.run(["git", "log", "--max-count=30", "--pretty=format:%h %s"], cwd=target, text=True, capture_output=True, timeout=20)
                diff = subprocess.run(["git", "diff", "--stat"], cwd=target, text=True, capture_output=True, timeout=20)
                git_summary = f"## Git signals\nRecent commits:\n```\n{log.stdout[:3000]}\n```\nCurrent diff stat:\n```\n{diff.stdout[:2000]}\n```"
            except Exception as exc:
                git_summary = f"## Git signals\nНе удалось прочитать git: {exc}"
        style_text = "\n\n".join(sections + ([git_summary] if git_summary else []))
        if not style_text.strip():
            style_text = "Конфигурационные файлы стиля не найдены. Используй аккуратный минималистичный стиль проекта, сохраняй существующие имена, форматирование и паттерны соседних файлов."
        report = f"""# Stella Team Style Guide\n\nСгенерировано: {dt.datetime.now().isoformat(timespec='seconds')}\nПроект: {target}\n\n## Правила для Stella\n\n1. Перед правкой читать соседние файлы и повторять их структуру, нейминг и форматирование.\n2. Соблюдать найденные настройки EditorConfig, ESLint, Prettier, Ruff, pyproject/setup.cfg.\n3. Коммиты и документацию писать в стиле последних сообщений Git.\n4. Если правила конфликтуют, приоритет: локальный файл проекта → существующий код → общепринятые правила языка.\n5. Не делать массовые переформатирования без прямого запроса.\n\n## Найденные источники\n\n{style_text}\n"""
        out = target / ".stella_style"
        out.write_text(report, encoding="utf-8")
        return ToolResult(True, f"Создан style-guide: {out.relative_to(self.root) if self.root in out.parents or out == self.root else out}\n\n" + report[:4000])

    def tool_spawn_agents(self, tasks: list[str]) -> ToolResult:
        if not isinstance(tasks, list) or not tasks:
            return ToolResult(False, "tasks должен быть непустым списком строк.")
        if len(tasks) > 8:
            return ToolResult(False, "За один запуск разрешено до 8 мини-агентов, чтобы не перегрузить компьютер.")
        if not self._approve(f"Запустить {len(tasks)} мини-агентов Stella с общей памятью?", risky=True):
            return ToolResult(False, "Пользователь отказался запускать мини-агентов.")
        shared_dir = self.root / ".stella" / "shared_context"
        shared_dir.mkdir(parents=True, exist_ok=True)
        shared_file = shared_dir / (dt.datetime.now().strftime("%Y%m%d-%H%M%S") + f"-{uuid.uuid4().hex[:8]}.jsonl")
        seed = {"time": dt.datetime.now().isoformat(timespec="seconds"), "role": "coordinator", "event": "start", "tasks": [str(t) for t in tasks]}
        shared_file.write_text(json.dumps(seed, ensure_ascii=False) + "\n", encoding="utf-8")
        results: list[tuple[int, str]] = []
        lock = threading.Lock()

        def read_shared_tail() -> str:
            try:
                lines = shared_file.read_text(encoding="utf-8", errors="replace").splitlines()[-20:]
                return "\n".join(lines)[-6000:]
            except OSError:
                return ""

        def append_shared(record: dict[str, Any]) -> None:
            with lock:
                with shared_file.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")

        def worker(i: int, task: str) -> None:
            context_tail = read_shared_tail()
            local_messages = [
                {"role": "system", "content": "Ты мини-агент Stella. Работай как узкий специалист, учитывай shared context, возвращай краткий полезный результат и явно перечисляй артефакты/риски. Отвечай по-русски."},
                {"role": "user", "content": f"Задача агента #{i}: {task[:4000]}\n\nSHARED_CONTEXT_TAIL:\n{context_tail}"},
            ]
            append_shared({"time": dt.datetime.now().isoformat(timespec="seconds"), "role": f"agent-{i}", "event": "started", "task": task})
            try:
                if self.provider == "openai" and OPENAI_API_KEY:
                    text = call_openai_once(local_messages, self.model if self.model != DEFAULT_MODEL else OPENAI_MODEL)
                else:
                    text = call_ollama_once(local_messages, self.model)
            except Exception as exc:
                text = f"Ошибка мини-агента: {exc}"
            append_shared({"time": dt.datetime.now().isoformat(timespec="seconds"), "role": f"agent-{i}", "event": "finished", "task": task, "result": text[:12000]})
            with lock:
                results.append((i, f"## Агент {i}\nЗадача: {task}\n\n{text}"))

        threads = [threading.Thread(target=worker, args=(i, str(task)), daemon=True) for i, task in enumerate(tasks, start=1)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=360)
        results.sort(key=lambda item: item[0])
        summary = "\n\n".join(text for _, text in results)
        return ToolResult(True, f"Shared context: {shared_file.relative_to(self.root)}\n\n{summary}")

    def tool_phone_devices(self) -> ToolResult:
        try:
            return ToolResult(True, json.dumps(adb_devices(), ensure_ascii=False, indent=2))
        except Exception as exc:
            return ToolResult(False, f"Ошибка phone_devices: {exc}")

    def tool_phone_shell(self, command: str, serial: str = "", timeout: int = 60) -> ToolResult:
        if not self._approve(f"выполнить adb shell на телефоне: {command}", risky=True):
            return ToolResult(False, "Отменено пользователем.")
        try:
            return ToolResult(True, json.dumps(adb_shell(command, serial or None, timeout=timeout), ensure_ascii=False, indent=2))
        except Exception as exc:
            return ToolResult(False, f"Ошибка phone_shell: {exc}")

    def tool_phone_tap(self, x: int, y: int, serial: str = "") -> ToolResult:
        if not self._approve(f"тапнуть телефон в координатах {x},{y}", risky=True):
            return ToolResult(False, "Отменено пользователем.")
        try:
            return ToolResult(True, json.dumps(adb_tap(x, y, serial or None), ensure_ascii=False, indent=2))
        except Exception as exc:
            return ToolResult(False, f"Ошибка phone_tap: {exc}")

    def tool_phone_swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300, serial: str = "") -> ToolResult:
        if not self._approve(f"свайпнуть телефон {x1},{y1}->{x2},{y2}", risky=True):
            return ToolResult(False, "Отменено пользователем.")
        try:
            return ToolResult(True, json.dumps(adb_swipe(x1, y1, x2, y2, duration_ms, serial or None), ensure_ascii=False, indent=2))
        except Exception as exc:
            return ToolResult(False, f"Ошибка phone_swipe: {exc}")

    def tool_phone_text(self, text: str, serial: str = "") -> ToolResult:
        if not self._approve(f"ввести текст на телефоне ({len(text)} символов)", risky=True):
            return ToolResult(False, "Отменено пользователем.")
        try:
            return ToolResult(True, json.dumps(adb_text(text, serial or None), ensure_ascii=False, indent=2))
        except Exception as exc:
            return ToolResult(False, f"Ошибка phone_text: {exc}")

    def tool_phone_keyevent(self, keycode: int | str, serial: str = "") -> ToolResult:
        if not self._approve(f"нажать Android keyevent {keycode}", risky=True):
            return ToolResult(False, "Отменено пользователем.")
        try:
            return ToolResult(True, json.dumps(adb_keyevent(keycode, serial or None), ensure_ascii=False, indent=2))
        except Exception as exc:
            return ToolResult(False, f"Ошибка phone_keyevent: {exc}")

    def tool_phone_screenshot(self, filename: str = "phone_screenshot.png", serial: str = "") -> ToolResult:
        try:
            result = adb_screenshot(filename, serial or None)
            return ToolResult(bool(result.get("ok")), json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as exc:
            return ToolResult(False, f"Ошибка phone_screenshot: {exc}")

    def tool_visual_qa(self, url: str, filename: str = 'visual_qa_screenshot.png', delay: int = 2) -> ToolResult:
        try:
            if not self._approve(f"открыть URL {url} и сделать скриншот в {filename}", risky=True):
                return ToolResult(ok=False, content="Отменено пользователем.")
            webbrowser.open(url)
            time.sleep(max(0, int(delay)))
            result = screenshot(filename)
            meta = visual_qa_metadata(result.get("path", filename) if isinstance(result, dict) else filename)
            checks = []
            if meta.get("ok"):
                if meta.get("width", 0) < 320 or meta.get("height", 0) < 240:
                    checks.append("warning: скриншот слишком маленький для полноценной QA-проверки")
                else:
                    checks.append("ok: скриншот получен и имеет рабочее разрешение")
            content = {"url": url, "screenshot": result, "metadata": meta, "checks": checks}
            return ToolResult(ok=True, content=json.dumps(content, ensure_ascii=False, indent=2))
        except Exception as e:
            return ToolResult(ok=False, content=f"Ошибка visual_qa: {e}")

    def tool_security_scan(self, url: str, type: str, parameter: str) -> ToolResult:
        try:
            if not self._approve(f"просканировать {url} на {type} (параметр {parameter})", risky=True):
                return ToolResult(ok=False, content="Отменено пользователем.")
            if type == 'sqli':
                vuln, msg = check_sql_injection(url, parameter)
            elif type == 'xss':
                vuln, msg = check_xss(url, parameter)
            else:
                return ToolResult(ok=False, content=f"Неизвестный тип сканирования: {type}")
            return ToolResult(ok=True, content=f"Результат сканирования: {'УЯЗВИМОСТЬ НАЙДЕНА' if vuln else 'Чисто'}. {msg}")
        except Exception as e:
            return ToolResult(ok=False, content=f"Ошибка security_scan: {e}")


    def tool_autopilot_plan(self, task: str, max_agents: int = 12) -> ToolResult:
        """Create an operator plan for a large/ambiguous task and save it to .stella."""
        try:
            payload = make_operator_plan(self.root, task=str(task or ""), max_agents=int(max_agents or 12))
            return ToolResult(True, json.dumps(payload, ensure_ascii=False, indent=2))
        except Exception as exc:
            return ToolResult(False, f"Ошибка autopilot_plan: {type(exc).__name__}: {exc}")

    def tool_autopilot_research(self, query: str, urls: list[str] | str | None = None, max_results: int = 8) -> ToolResult:
        """Search and fetch public sources for a task; stores .stella/research_notes.json."""
        if isinstance(urls, str):
            try:
                urls_obj = json.loads(urls)
                urls = urls_obj if isinstance(urls_obj, list) else [urls]
            except json.JSONDecodeError:
                urls = [item.strip() for item in urls.split() if item.strip().startswith(("http://", "https://"))]
        try:
            payload = autopilot_research(self.root, query=str(query or ""), urls=urls if isinstance(urls, list) else [], max_results=int(max_results or 8))
            return ToolResult(True, json.dumps(payload, ensure_ascii=False, indent=2)[:MAX_COMMAND_OUTPUT])
        except Exception as exc:
            return ToolResult(False, f"Ошибка autopilot_research: {type(exc).__name__}: {exc}")

    def tool_github_scan(self, repo_url: str, max_files: int = 80) -> ToolResult:
        """Scan a public GitHub repository through GitHub API without executing code."""
        try:
            payload = autopilot_github_scan(self.root, repo_url=str(repo_url or ""), max_files=int(max_files or 80))
            return ToolResult(True, json.dumps(payload, ensure_ascii=False, indent=2)[:MAX_COMMAND_OUTPUT])
        except Exception as exc:
            return ToolResult(False, f"Ошибка github_scan: {type(exc).__name__}: {exc}")

    def tool_draft_report(self, recipient: str, subject: str, summary: str, attachments: list[str] | str | None = None, messenger: str = "telegram") -> ToolResult:
        """Prepare a report/message draft. Real sending must be confirmed and done through GUI/Telegram tools."""
        if isinstance(attachments, str):
            try:
                parsed = json.loads(attachments)
                attachments = parsed if isinstance(parsed, list) else [attachments]
            except json.JSONDecodeError:
                attachments = [line.strip() for line in attachments.splitlines() if line.strip()]
        try:
            payload = autopilot_draft_report(self.root, recipient=recipient, subject=subject, summary=summary, attachments=attachments if isinstance(attachments, list) else [], messenger=messenger)
            return ToolResult(True, json.dumps(payload, ensure_ascii=False, indent=2))
        except Exception as exc:
            return ToolResult(False, f"Ошибка draft_report: {type(exc).__name__}: {exc}")


    def tool_telegram_action(self, recipient: str, message: str, attachments: list[str] | str | None = None) -> ToolResult:
        """Prepare a Telegram action. Stella may open Telegram, but final send needs explicit user confirmation."""
        if isinstance(attachments, str):
            try:
                parsed = json.loads(attachments)
                attachments = parsed if isinstance(parsed, list) else [attachments]
            except json.JSONDecodeError:
                attachments = [line.strip() for line in attachments.splitlines() if line.strip()]
        try:
            payload = prepare_telegram_action(self.root, recipient=recipient, message=message, attachments=attachments if isinstance(attachments, list) else [])
            return ToolResult(True, json.dumps(payload, ensure_ascii=False, indent=2))
        except Exception as exc:
            return ToolResult(False, f"Ошибка telegram_action: {type(exc).__name__}: {exc}")

    def tool_home_assistant_action(self, base_url: str = "", token_env: str = "HOME_ASSISTANT_TOKEN", domain: str = "", service: str = "", entity_id: str = "", data: dict[str, Any] | str | None = None, dry_run: bool = True) -> ToolResult:
        """Prepare or execute a Home Assistant service call; real execution requires confirmation and env token."""
        if isinstance(data, str):
            try:
                data_obj = json.loads(data) if data.strip() else {}
            except json.JSONDecodeError as exc:
                return ToolResult(False, f"data должен быть JSON: {exc}")
        else:
            data_obj = data if isinstance(data, dict) else {}
        dry_run_bool = bool(dry_run)
        if not dry_run_bool:
            if not self._approve(f"Выполнить Home Assistant service call {domain}.{service} для {entity_id or 'без entity_id'}?", risky=True):
                return ToolResult(False, "Пользователь отказался выполнять Home Assistant действие.")
        try:
            payload = home_assistant_call(self.root, base_url=base_url, token_env=token_env, domain=domain, service=service, entity_id=entity_id, data=data_obj, dry_run=dry_run_bool)
            return ToolResult(bool(payload.get("ok")), json.dumps(payload, ensure_ascii=False, indent=2))
        except Exception as exc:
            return ToolResult(False, f"Ошибка home_assistant_action: {type(exc).__name__}: {exc}")

    def tool_operator_action(self, action: str, details: dict[str, Any] | str | None = None, sensitive: bool = True) -> ToolResult:
        """Log and gate a real-world action such as payment, messaging, account creation, SSH or device control."""
        if isinstance(details, str):
            try:
                details_obj = json.loads(details)
            except json.JSONDecodeError:
                details_obj = {"text": details}
        elif isinstance(details, dict):
            details_obj = details
        else:
            details_obj = {}
        risk = classify_task(str(action) + "\n" + json.dumps(details_obj, ensure_ascii=False))
        if risk.get("blocked"):
            append_operator_log(self.root, "operator_action_blocked", {"action": action, "details": details_obj, "risk": risk})
            return ToolResult(False, "Действие похоже на вредное/нелегальное. Stella может предложить безопасную альтернативу, аудит или защитный сценарий.")
        needs_confirm = bool(sensitive) or bool(risk.get("requires_confirmation"))
        if needs_confirm and not self._approve(f"Подтвердить реальное действие: {action}? Детали будут записаны в журнал.", risky=True):
            append_operator_log(self.root, "operator_action_cancelled", {"action": action, "details": details_obj, "risk": risk})
            return ToolResult(False, "Пользователь не подтвердил чувствительное действие.")
        log_file = append_operator_log(self.root, "operator_action_confirmed" if needs_confirm else "operator_action", {"action": action, "details": details_obj, "risk": risk})
        return ToolResult(True, f"Действие разрешено для следующего шага и записано в журнал: {log_file}\nВажно: платежи/сообщения/аккаунты выполняй только прозрачно, по шагам, с видимым подтверждением пользователя.")

    def tool_connector_profile(self, kind: str, name: str, config: dict[str, Any] | str) -> ToolResult:
        """Create a disabled connector profile for server, Home Assistant, API or device integration."""
        if isinstance(config, str):
            try:
                config_obj = json.loads(config)
            except json.JSONDecodeError as exc:
                return ToolResult(False, f"config должен быть JSON: {exc}")
        else:
            config_obj = config if isinstance(config, dict) else {}
        try:
            payload = create_connector_profile(self.root, kind=kind, name=name, config=config_obj)
            return ToolResult(True, json.dumps(payload, ensure_ascii=False, indent=2))
        except Exception as exc:
            return ToolResult(False, f"Ошибка connector_profile: {type(exc).__name__}: {exc}")

    def tool_pixel_agents_install(self, mode: str = "prepare") -> ToolResult:
        """Clone/build Pixel Agents source from GitHub and prepare the real-time viewer integration."""
        if not self._approve("Скачать/обновить и собрать Pixel Agents из GitHub? Это запустит git/npm install/npm build.", risky=True):
            return ToolResult(False, "Пользователь отказался устанавливать Pixel Agents.")
        try:
            payload = autopilot_install_pixel_agents(self.root, mode=mode)
            return ToolResult(bool(payload.get("ok")), json.dumps(payload, ensure_ascii=False, indent=2)[:MAX_COMMAND_OUTPUT])
        except Exception as exc:
            return ToolResult(False, f"Ошибка pixel_agents_install: {type(exc).__name__}: {exc}")

    def tool_live_actions_viewer(self) -> ToolResult:
        """Create an auto-refreshing HTML view of Stella operator actions."""
        try:
            payload = make_live_viewer(self.root, native_log=str(self.root / ".stella" / "operator_actions.jsonl"), pixel_log=str(self.pixel_session_file))
            return ToolResult(True, json.dumps(payload, ensure_ascii=False, indent=2))
        except Exception as exc:
            return ToolResult(False, f"Ошибка live_actions_viewer: {type(exc).__name__}: {exc}")

    def _approve(self, question: str, risky: bool = True) -> bool:
        if self.approval_mode == "readonly":
            return not risky
        if self.approval_mode == "auto":
            return True
        return Confirm.ask(question, default=not risky)

    def _print_tool_result(self, name: str, args: dict[str, Any], result: ToolResult) -> None:
        arg_text = json.dumps(redact_secrets(args), ensure_ascii=False)
        content = result.content[:2200]
        color = "green" if result.ok else "red"
        console.print(Panel(f"[dim]{escape_rich(arg_text)}[/dim]\n\n{escape_rich(content)}", title=f"инструмент: {name} [{'готово' if result.ok else 'ошибка'}]", border_style=color, box=box.ROUNDED))

def call_ollama_once(messages: list[dict[str, str]], model: str) -> str:
    response = requests.post(f"{OLLAMA_URL}/api/chat", json={"model": model, "messages": messages, "stream": False, "options": {"temperature": 0.2, "num_ctx": 8192}}, timeout=240)
    response.raise_for_status()
    return response.json().get("message", {}).get("content", "").strip()

def call_openai_once(messages: list[dict[str, str]], model: str) -> str:
    response = requests.post(f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions", headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}, json={"model": model, "messages": messages, "temperature": 0.2}, timeout=240)
    response.raise_for_status()
    return response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()

def parse_json_object(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None

def classify_command(command: str) -> str:
    text = command.strip()
    if not text:
        return "blocked"
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return "blocked"
    lower = text.lower()
    if re.match(r"^git\s+(status|diff|log|show|branch|remote|rev-parse|ls-files|grep|blame)\b", lower):
        return "auto"
    first = split_first_command(text)
    if first in AUTO_SAFE_COMMANDS:
        return "auto"
    if first in CONFIRM_COMMANDS:
        return "confirm"
    return "confirm"

def split_first_command(text: str) -> str:
    try:
        parts = shlex.split(text, posix=(platform.system().lower() != "windows"))
    except ValueError:
        parts = text.split()
    if not parts:
        return ""
    return Path(parts[0]).name.lower()

def check_ollama(model: str, quiet: bool = False) -> bool:
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
    except requests.RequestException:
        if not quiet:
            console.print(Panel("Ollama не отвечает. Установи Ollama и выполни `ollama serve`, затем `ollama pull " + model + "`.", title="Ollama offline", border_style="red"))
        return False
    if response.status_code >= 400:
        if not quiet:
            console.print(f"[red]Ошибка Ollama:[/red] {response.status_code}")
        return False
    names = {item.get("name") for item in response.json().get("models", [])}
    if model not in names and not any(str(name).split(":")[0] == model.split(":")[0] for name in names if name):
        if not quiet:
            console.print(Panel(f"Модель `{model}` ещё не установлена. Выполни: ollama pull {model}", title="Модель не найдена", border_style="yellow"))
        return False
    return True

def maybe_offer_pixel_agents_first_run() -> None:
    marker_dir = Path.home() / ".stella-ai-coder"
    marker = marker_dir / ".pixel_first_run_checked"
    if marker.exists() or os.getenv("STELLA_SKIP_PIXEL_PROMPT", "").lower() in {"1", "true", "yes"}:
        return
    marker_dir.mkdir(parents=True, exist_ok=True)
    try:
        marker.write_text(dt.datetime.now().isoformat(timespec="seconds"), encoding="utf-8")
    except OSError:
        pass
    console.print(Panel(
        "Stella может подготовить Pixel Agents: открыть VS Code extension, клонировать исходники из GitHub "
        "и вести Autopilot live-viewer действий. Это действие требует Git/npm и выполняется только по твоему согласию.",
        title="Pixel Agents first run", border_style="cyan", box=box.ROUNDED
    ))

def print_banner(model: str, provider: str, root: Path, approval_mode: str) -> None:
    console.print(Text(ASCII_ART, style="bold bright_magenta"))
    body = (
        f"[bold bright_cyan]{APP_NAME}[/bold bright_cyan] [dim]v{APP_VERSION}[/dim]\n"
        f"[cyan]provider[/cyan]: {provider}    [cyan]модель[/cyan]: {model}\n"
        f"[cyan]проект[/cyan]: {root}\n"
        f"[cyan]подтверждения[/cyan]: {approval_mode}\n\n"
        "Пиши обычным языком. Stella умеет читать/править код, запускать команды, Git, web, GUI, SSH/deploy, style-guide, bot sandbox, pixel-agents, Autopilot/Operator и мини-агентов."
    )
    console.print(Panel(Align.left(body), border_style="bright_magenta", box=box.DOUBLE))

def print_help() -> None:
    table = Table(title="Stella AI Agent 3.8 — команды и инструменты", box=box.ROUNDED, border_style="cyan")
    table.add_column("Команда / инструмент", style="bold magenta")
    table.add_column("Что делает", style="white")
    rows = [
        ("/помощь, /help", "Показать справку"),
        ("/доктор", "Проверить Python, provider, модель, Git, Node, Docker, SSH, pixel-agents"),
        ("/модель NAME", "Сменить модель"),
        ("/provider ollama|openai", "Сменить движок модели"),
        ("/папка PATH", "Сменить активную папку проекта"),
        ("/дерево [path] [depth]", "Показать дерево проекта"),
        ("/список [path]", "Показать файлы"),
        ("/обзор", "Автоанализ проекта"),
        ("/git", "Показать git status"),
        ("/pixel", "Статус pixel-agents; /pixel start запускает companion UI"),
        ("/autopilot TASK", "Построить Operator-план задачи, risk-классификацию и журнал действий"),
        ("/live", "Создать HTML-viewer действий Stella в .stella/live_actions.html"),
        ("/sessions", "Показать путь к истории сессии"),
        ("Файлы", "list_dir, tree, read_file, write_file, edit_file, search_text"),
        ("Терминал/Git", "run_command, git_status, git_diff, git_log, git_commit"),
        ("Интернет/компьютер", "web_search, web_fetch, open_url, open_app"),
        ("Агенты/Enterprise", "create_plan, update_plan, spawn_agents, analyze_style, bot_sandbox, ssh_run, deploy_app, pixel_agents_start"),
        ("Autopilot/Operator", "autopilot_plan, autopilot_research, github_scan, draft_report, telegram_action, home_assistant_action, operator_action, connector_profile, pixel_agents_install, live_actions_viewer"),
        ("GUI/QA/Security", "move_mouse, click, type_text, screenshot, phone_*, visual_qa, security_scan"),
    ]
    for row in rows:
        table.add_row(*row)
    console.print(table)

def print_doctor(agent: StellaAgent) -> None:
    table = Table(title="Диагностика Stella", box=box.ROUNDED, border_style="cyan")
    table.add_column("Проверка", style="bold magenta")
    table.add_column("Результат", style="white")
    table.add_row("Stella", APP_VERSION)
    table.add_row("Python", sys.version.split()[0])
    table.add_row("OS", f"{platform.system()} {platform.release()}")
    table.add_row("Provider", agent.provider)
    table.add_row("Ollama API", "готово" if requests_ok(f"{OLLAMA_URL}/api/tags") else "не отвечает")
    table.add_row("Ollama model", f"{agent.model} готова" if check_ollama(agent.model, quiet=True) else f"{agent.model} не найдена/offline")
    table.add_row("OpenAI API key", "задан" if OPENAI_API_KEY else "не задан")
    for cmd in ["git", "gh", "docker", "docker-compose", "node", "npm", "npx", "ssh", "nginx", "ollama", "adb"]:
        table.add_row(cmd, shutil.which(cmd) or "не найден")
    table.add_row("Session", str(agent.session_file))
    console.print(table)

def requests_ok(url: str) -> bool:
    try:
        response = requests.get(url, timeout=4)
        return response.status_code < 500
    except requests.RequestException:
        return False

def render_answer(text: str) -> None:
    if "```" in text or text.lstrip().startswith(("#", "-", "1.", "|")):
        console.print(Panel(Markdown(text), title="Stella", border_style="bright_cyan", box=box.ROUNDED))
    else:
        console.print(Panel(escape_rich(text), title="Stella", border_style="bright_cyan", box=box.ROUNDED))

def render_tool_panel(title: str, result: ToolResult) -> None:
    color = "green" if result.ok else "red"
    console.print(Panel(escape_rich(result.content), title=title, border_style=color, box=box.ROUNDED))

def escape_rich(text: str) -> str:
    return str(text).replace("[", "\\[").replace("]", "\\]")

def strip_html(text: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return html_lib.unescape(re.sub(r"\s+", " ", text)).strip()

def html_to_text(text: str) -> str:
    title = ""
    m = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.I | re.S)
    if m:
        title = strip_html(m.group(1))
    body = strip_html(text)
    return (f"Title: {title}\n\n" if title else "") + body

def human_size(num: int) -> str:
    value = float(num)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024:
            return f"{value:.0f}{unit}" if unit == "B" else f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}TB"

def redact_secrets(obj: Any) -> Any:
    secret_words = ("key", "token", "secret", "password", "passwd", "authorization", "cookie")
    if isinstance(obj, dict):
        return {k: ("***" if any(w in str(k).lower() for w in secret_words) else redact_secrets(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_secrets(x) for x in obj]
    return obj

def looks_like_project_question(text: str) -> bool:
    lower = text.lower()
    markers = ["расскажи про проект", "что за проект", "что в этой папке", "проанализируй проект", "обзор проекта", "посмотри проект", "изучи проект", "разбери проект", "анализ проекта"]
    return any(marker in lower for marker in markers)

def looks_like_false_no_access(text: str) -> bool:
    lower = text.lower()
    markers = ["не вижу файлы", "не имею доступа к файлам", "не вижу папки", "не могу видеть файлы", "нет доступа к проекту"]
    return any(marker in lower for marker in markers)

def normalize_approval_mode(value: str) -> str:
    aliases = {
        "ask": "suggest",
        "suggest": "suggest",
        "auto": "auto",
        "danger": "auto",
        "never": "readonly",
        "readonly": "readonly",
    }
    return aliases.get((value or "suggest").strip().lower(), "suggest")

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stella AI Agent 3.8 Enterprise Autopilot")
    parser.add_argument("model_arg", nargs="?", help="Необязательное имя модели")
    parser.add_argument("--model", dest="model", help="Имя модели")
    parser.add_argument("--provider", choices=["ollama", "openai"], default=DEFAULT_PROVIDER, help="LLM provider")
    parser.add_argument("--root", dest="root", help="Папка проекта")
    parser.add_argument("--approval", choices=["suggest", "ask", "auto", "readonly", "never", "danger"], default=os.getenv("STELLA_APPROVAL_MODE", os.getenv("STELLA_APPROVAL", "suggest")), help="Режим подтверждений")
    parser.add_argument("--version", action="store_true", help="Показать версию")
    return parser.parse_args(argv)

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.version:
        console.print(f"{APP_NAME} {APP_VERSION}")
        return 0
    model = args.model or args.model_arg or (OPENAI_MODEL if args.provider == "openai" else DEFAULT_MODEL)
    root = Path(args.root).expanduser().resolve() if args.root else Path.cwd().resolve()
    args.approval = normalize_approval_mode(args.approval)
    print_banner(model, args.provider, root, args.approval)
    maybe_offer_pixel_agents_first_run()
    if args.provider == "ollama" and not check_ollama(model):
        console.print("[yellow]Stella запустится после установки/запуска Ollama. Сейчас выход.[/yellow]")
        return 1
    if args.provider == "openai" and not OPENAI_API_KEY:
        console.print(Panel("Для provider=openai нужен OPENAI_API_KEY.", title="Нет API ключа", border_style="red"))
        return 1
    agent = StellaAgent(model=model, provider=args.provider, root=root, approval_mode=args.approval)
    print_help()
    while True:
        try:
            user_text = Prompt.ask("\n[bold bright_green]ты[/bold bright_green]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[magenta]Пока. Stella выключается.[/magenta]")
            return 0
        if not user_text:
            continue
        lower = user_text.lower().strip()
        if lower in {"/exit", "exit", "quit", "/выход", "выход"}:
            console.print("[magenta]Пока. Stella выключается.[/magenta]")
            return 0
        if lower in {"/help", "/помощь", "/команды"}:
            print_help(); continue
        if lower in {"/doctor", "/доктор", "/диагностика"}:
            print_doctor(agent); continue
        if lower in {"/pwd", "/где", "/папка?"}:
            console.print(Panel(str(agent.root), title="Папка проекта", border_style="cyan")); continue
        if lower in {"/clear", "/очистить"}:
            agent.clear(); console.print("[green]Контекст очищен.[/green]"); continue
        if lower in {"/sessions", "/сессии"}:
            console.print(Panel(str(agent.session_file), title="История сессии", border_style="cyan")); continue
        if lower.startswith("/tree") or lower.startswith("/дерево"):
            parts = user_text.split(); path = parts[1] if len(parts) >= 2 else "."; depth = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else 3
            render_tool_panel("Дерево проекта", agent.tool_tree(path, depth)); continue
        if lower.startswith("/ls") or lower.startswith("/список"):
            parts = user_text.split(maxsplit=1); path = parts[1].strip() if len(parts) == 2 else "."
            render_tool_panel("Список файлов", agent.tool_list_dir(path)); continue
        if lower.startswith("/find") or lower.startswith("/найти"):
            parts = user_text.split(maxsplit=1)
            render_tool_panel("Найденные файлы", agent.tool_find_files(parts[1].strip() if len(parts) == 2 else "")); continue
        if lower.startswith("/search") or lower.startswith("/поиск"):
            parts = user_text.split(maxsplit=1)
            if len(parts) == 1: console.print("[yellow]Использование: /поиск текст_или_regex[/yellow]"); continue
            render_tool_panel("Поиск по файлам", agent.tool_search_text(parts[1].strip())); continue
        if lower in {"/обзор", "/overview", "/анализ"}:
            try: answer = agent.chat("Проанализируй проект: технологии, структура, как запускать, риски и следующие шаги.")
            except Exception as exc: console.print(Panel(f"{type(exc).__name__}: {exc}", title="Ошибка", border_style="red")); continue
            render_answer(answer); continue
        if lower in {"/git", "/status"}:
            render_tool_panel("Git status", agent.tool_git_status()); continue
        if lower.startswith("/pixel"):
            if "start" in lower or "запуск" in lower:
                render_tool_panel("Pixel Agents", agent.tool_pixel_agents_start())
            else:
                render_tool_panel("Pixel Agents", agent.tool_pixel_agents_status())
            continue
        if lower.startswith("/model") or lower.startswith("/модель"):
            parts = user_text.split(maxsplit=1)
            if len(parts) == 1: console.print(Panel(agent.model, title="Текущая модель", border_style="cyan")); continue
            agent.set_model(parts[1].strip())
            if agent.provider == "ollama": check_ollama(agent.model)
            console.print(f"[green]Модель переключена на {agent.model}[/green]"); continue
        if lower.startswith("/provider") or lower.startswith("/провайдер"):
            parts = user_text.split(maxsplit=1)
            if len(parts) == 1: console.print(Panel(agent.provider, title="Текущий provider", border_style="cyan")); continue
            try: agent.set_provider(parts[1].strip())
            except ValueError as exc: console.print(f"[red]{exc}[/red]"); continue
            console.print(f"[green]Provider переключен на {agent.provider}[/green]"); continue
        if lower.startswith("/cd") or lower.startswith("/папка"):
            parts = user_text.split(maxsplit=1)
            if len(parts) == 1: console.print("[yellow]Использование: /папка PATH[/yellow]"); continue
            new_root = Path(parts[1]).expanduser().resolve()
            if not new_root.exists() or not new_root.is_dir(): console.print(f"[red]Папка не найдена:[/red] {new_root}"); continue
            agent.set_root(new_root); console.print(f"[green]Папка проекта изменена:[/green] {new_root}"); continue
        try:
            answer = agent.chat(user_text)
        except RuntimeError as exc:
            console.print(Panel(str(exc), title="Ошибка", border_style="red")); continue
        except Exception as exc:
            console.print(Panel(f"{type(exc).__name__}: {exc}", title="Неожиданная ошибка", border_style="red")); continue
        render_answer(answer)

if __name__ == "__main__":
    raise SystemExit(main())
