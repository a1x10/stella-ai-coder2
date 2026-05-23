"""Autopilot/Operator helpers for Stella AI Agent.

This module gives Stella a practical operator layer: structured task planning,
transparent action logs, internet/source scanning, report drafting, connector
profiles and a local HTML viewer. Sensitive real-world actions are deliberately
returned as confirmation-ready plans instead of being executed silently.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import shutil
import subprocess
import textwrap
import urllib.parse
from pathlib import Path
from typing import Any

import requests

SENSITIVE_KEYWORDS = {
    "payment", "pay", "buy", "purchase", "order", "pizza", "subscribe", "subscription",
    "telegram", "whatsapp", "send message", "email", "sms", "account", "login", "password",
    "proton", "vpn", "ssh", "server", "home assistant", "smart home", "device", "camera",
    "плат", "купи", "закаж", "пицц", "подпис", "аккаунт", "логин", "парол", "отправ",
    "телеграм", "ватсап", "сервер", "умный дом", "устройство", "впн",
}

BLOCKED_KEYWORDS = {
    "steal", "token grab", "phishing", "malware", "ransomware", "ddos", "spam", "bypass auth",
    "укради", "фишинг", "вирус", "вредонос", "ддос", "спам", "обойти авторизац",
}


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def ensure_stella_dir(root: Path) -> Path:
    path = root / ".stella"
    path.mkdir(parents=True, exist_ok=True)
    return path


def append_operator_log(root: Path, event: str, data: dict[str, Any]) -> Path:
    path = ensure_stella_dir(root) / "operator_actions.jsonl"
    record = {"time": now(), "event": event, "data": redact(data)}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def redact(obj: Any) -> Any:
    words = ("key", "token", "secret", "password", "passwd", "authorization", "cookie", "card", "cvv")
    if isinstance(obj, dict):
        return {k: ("***" if any(w in str(k).lower() for w in words) else redact(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    return obj


def classify_task(task: str) -> dict[str, Any]:
    lower = (task or "").lower()
    blocked = [word for word in BLOCKED_KEYWORDS if word in lower]
    sensitive = [word for word in SENSITIVE_KEYWORDS if word in lower]
    return {
        "blocked": bool(blocked),
        "blocked_matches": blocked[:12],
        "sensitive": bool(sensitive),
        "sensitive_matches": sensitive[:12],
        "requires_confirmation": bool(sensitive),
    }


def make_operator_plan(root: Path, task: str, max_agents: int = 12) -> dict[str, Any]:
    risk = classify_task(task)
    if risk["blocked"]:
        steps = [
            "Остановить выполнение потенциально вредного сценария.",
            "Предложить безопасную альтернативу: аудит, защита, легальная автоматизация или учебное объяснение.",
        ]
    else:
        steps = [
            "Понять цель, входные данные, дедлайн, критерии успеха и ограничения.",
            "Собрать факты: файлы проекта, ссылки, документацию, GitHub-репозитории и публичные источники.",
            "Разбить работу на подзадачи и назначить мини-агентов для исследования, реализации, QA и отчёта.",
            "Внести изменения в отдельной рабочей папке или текущем проекте, сохраняя журнал действий.",
            "Запустить проверки: syntax/lint/tests/build/visual QA/security smoke по необходимости.",
            "Подготовить отчёт, артефакты и список выполненных действий.",
        ]
        if risk["sensitive"]:
            steps.append("Перед платежом, отправкой сообщения, созданием аккаунта или управлением устройством запросить явное подтверждение пользователя.")
    agent_count = max(1, min(int(max_agents or 12), 100))
    plan = {
        "task": task,
        "mode": "blocked-safe-alternative" if risk["blocked"] else "autopilot-operator",
        "risk": risk,
        "recommended_agent_count": agent_count,
        "steps": steps,
        "artifacts": [".stella/operator_actions.jsonl", ".stella/autopilot_plan.json"],
    }
    out = ensure_stella_dir(root) / "autopilot_plan.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    append_operator_log(root, "autopilot_plan", plan)
    return plan


def duckduckgo_search(query: str, max_results: int = 8) -> list[dict[str, str]]:
    url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    response = requests.get(url, timeout=35, headers={"User-Agent": "Mozilla/5.0 Stella-Autopilot/3.8"})
    response.raise_for_status()
    blocks = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', response.text, re.I | re.S)
    results: list[dict[str, str]] = []
    for raw_href, raw_title in blocks:
        href = html.unescape(raw_href)
        parsed = urllib.parse.urlparse(href)
        params = urllib.parse.parse_qs(parsed.query)
        if "uddg" in params:
            href = params["uddg"][0]
        title = strip_html(raw_title)
        if title and href:
            results.append({"title": title, "url": href})
        if len(results) >= max(1, min(int(max_results), 20)):
            break
    return results


def fetch_text(url: str, max_chars: int = 20000) -> str:
    if not re.match(r"^https?://", url or ""):
        raise ValueError("URL должен начинаться с http:// или https://")
    response = requests.get(url, timeout=45, headers={"User-Agent": "Mozilla/5.0 Stella-Autopilot/3.8"})
    response.raise_for_status()
    text = response.text
    if "html" in response.headers.get("content-type", "").lower():
        text = strip_html(text)
    return text[:max_chars] + ("\n\n[обрезано]" if len(text) > max_chars else "")


def research(root: Path, query: str, urls: list[str] | None = None, max_results: int = 8) -> dict[str, Any]:
    sources = []
    if query:
        for item in duckduckgo_search(query, max_results=max_results):
            sources.append({**item, "kind": "search"})
    for url in urls or []:
        sources.append({"title": url, "url": url, "kind": "user"})
    notes = []
    for source in sources[: max(1, min(len(sources), 12))]:
        try:
            text = fetch_text(source["url"], max_chars=12000)
            notes.append({"source": source, "excerpt": text[:4000]})
        except Exception as exc:
            notes.append({"source": source, "error": str(exc)})
    out = ensure_stella_dir(root) / "research_notes.json"
    payload = {"query": query, "created_at": now(), "sources": sources, "notes": notes}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    append_operator_log(root, "research", {"query": query, "source_count": len(sources), "notes": len(notes), "file": str(out)})
    return payload


def strip_html(text: str) -> str:
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def parse_github_url(url: str) -> tuple[str, str]:
    match = re.search(r"github\.com[:/]([^/]+)/([^/#?]+)", url or "")
    if not match:
        raise ValueError("Нужна ссылка вида https://github.com/owner/repo")
    owner = match.group(1)
    repo = match.group(2).removesuffix(".git")
    return owner, repo


def github_scan(root: Path, repo_url: str, max_files: int = 80) -> dict[str, Any]:
    owner, repo = parse_github_url(repo_url)
    api = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Stella-Autopilot/3.8"}
    meta = requests.get(api, headers=headers, timeout=35)
    meta.raise_for_status()
    meta_json = meta.json()
    branch = meta_json.get("default_branch", "main")
    tree = requests.get(f"{api}/git/trees/{branch}?recursive=1", headers=headers, timeout=45)
    tree.raise_for_status()
    files = []
    for item in tree.json().get("tree", []):
        if item.get("type") == "blob":
            path = item.get("path", "")
            if any(path.endswith(ext) for ext in (".md", ".py", ".js", ".ts", ".tsx", ".json", ".yml", ".yaml", ".toml", ".sh", ".ps1")):
                files.append({"path": path, "size": item.get("size", 0), "url": item.get("url", "")})
        if len(files) >= max(1, min(int(max_files), 300)):
            break
    important = [f for f in files if Path(f["path"]).name.lower() in {"readme.md", "package.json", "pyproject.toml", "requirements.txt", "dockerfile", "docker-compose.yml"}]
    payload = {"repo": repo_url, "owner": owner, "name": repo, "description": meta_json.get("description"), "stars": meta_json.get("stargazers_count"), "default_branch": branch, "important_files": important, "sample_files": files[:50]}
    out = ensure_stella_dir(root) / "github_scan.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    append_operator_log(root, "github_scan", {"repo": repo_url, "files": len(files), "file": str(out)})
    return payload


def draft_report(root: Path, recipient: str, subject: str, summary: str, attachments: list[str] | None = None, messenger: str = "telegram") -> dict[str, Any]:
    attachments = attachments or []
    safe_recipient = re.sub(r"[^A-Za-z0-9_@+ .-]+", "", recipient or "").strip()
    text = textwrap.dedent(f"""
    Получатель: {safe_recipient}
    Канал: {messenger}
    Тема: {subject}

    {summary}

    Вложения/пути:
    {chr(10).join('- ' + item for item in attachments) if attachments else '- нет'}

    Примечание: это черновик. Реальная отправка сообщения, файлов или кода требует явного подтверждения владельца.
    """).strip()
    out = ensure_stella_dir(root) / "report_draft.md"
    out.write_text(text + "\n", encoding="utf-8")
    append_operator_log(root, "report_draft", {"recipient": safe_recipient, "messenger": messenger, "file": str(out), "attachments": attachments})
    return {"ok": True, "draft_file": str(out), "text": text}


def create_connector_profile(root: Path, kind: str, name: str, config: dict[str, Any]) -> dict[str, Any]:
    kind = re.sub(r"[^a-z0-9_-]+", "-", (kind or "generic").lower()).strip("-") or "generic"
    name = re.sub(r"[^A-Za-z0-9_.-]+", "-", name or "default").strip("-") or "default"
    path = ensure_stella_dir(root) / "connectors" / kind
    path.mkdir(parents=True, exist_ok=True)
    profile = {"kind": kind, "name": name, "created_at": now(), "config": redact(config), "status": "created-disabled-until-user-confirms"}
    out = path / f"{name}.json"
    out.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    append_operator_log(root, "connector_profile", {"kind": kind, "name": name, "file": str(out)})
    return {"ok": True, "file": str(out), "profile": profile}


def install_pixel_agents(root: Path, mode: str = "prepare") -> dict[str, Any]:
    base = Path.home() / ".stella-ai-coder" / "pixel-agents"
    base.parent.mkdir(parents=True, exist_ok=True)
    commands: list[list[str]] = []
    logs: list[str] = []
    if not shutil.which("git"):
        return {"ok": False, "error": "git не найден"}
    if not shutil.which("npm"):
        return {"ok": False, "error": "npm не найден"}
    if (base / ".git").exists():
        commands.append(["git", "pull", "--ff-only"])
        cwd0 = base
    else:
        commands.append(["git", "clone", "https://github.com/pixel-agents-hq/pixel-agents.git", str(base)])
        cwd0 = base.parent
    for i, cmd in enumerate(commands):
        cwd = cwd0 if i == 0 else base
        completed = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=300)
        logs.append(f"$ {' '.join(cmd)} cwd={cwd} exit={completed.returncode}\n{(completed.stdout + completed.stderr)[-4000:]}")
        if completed.returncode != 0:
            append_operator_log(root, "pixel_agents_install", {"ok": False, "logs": logs})
            return {"ok": False, "path": str(base), "logs": logs}
    for cmd, cwd in [(["npm", "install"], base), (["npm", "install"], base / "webview-ui"), (["npm", "run", "build"], base)]:
        if not cwd.exists():
            logs.append(f"skip {' '.join(cmd)}: {cwd} not found")
            continue
        completed = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=900)
        logs.append(f"$ {' '.join(cmd)} cwd={cwd} exit={completed.returncode}\n{(completed.stdout + completed.stderr)[-4000:]}")
        if completed.returncode != 0:
            append_operator_log(root, "pixel_agents_install", {"ok": False, "logs": logs})
            return {"ok": False, "path": str(base), "logs": logs}
    append_operator_log(root, "pixel_agents_install", {"ok": True, "path": str(base)})
    return {"ok": True, "path": str(base), "mode": mode, "logs": logs}


def make_live_viewer(root: Path, native_log: str | None = None, pixel_log: str | None = None) -> dict[str, Any]:
    stella = ensure_stella_dir(root)
    html_path = stella / "live_actions.html"
    native = native_log or str(stella / "operator_actions.jsonl")
    pixel = pixel_log or ""
    content = f"""<!doctype html>
<html lang=\"ru\"><head><meta charset=\"utf-8\"><meta http-equiv=\"refresh\" content=\"3\">
<title>Stella Live Actions</title><style>body{{font-family:system-ui,Arial;background:#0f172a;color:#e5e7eb;margin:24px}}pre{{white-space:pre-wrap;background:#111827;border:1px solid #334155;padding:16px;border-radius:12px}}.card{{margin-bottom:18px}}</style></head>
<body><h1>Stella AI — live actions viewer</h1><p>Файл автообновляется каждые 3 секунды. Открой его в браузере или через Pixel Agents/VS Code.</p>
<div class=\"card\"><b>Native operator log:</b> {html.escape(native)}</div><div class=\"card\"><b>Pixel JSONL:</b> {html.escape(pixel)}</div>
<h2>Последние operator actions</h2><pre>{html.escape(tail_file(Path(native), 120))}</pre>
</body></html>"""
    html_path.write_text(content, encoding="utf-8")
    append_operator_log(root, "live_viewer", {"file": str(html_path), "native_log": native, "pixel_log": pixel})
    return {"ok": True, "file": str(html_path), "native_log": native, "pixel_log": pixel}


def tail_file(path: Path, lines: int = 80) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(data[-lines:]) if data else "Лог пока пуст."
    except OSError:
        return "Лог пока не создан."


def prepare_telegram_action(root: Path, recipient: str, message: str, attachments: list[str] | None = None) -> dict[str, Any]:
    """Prepare a transparent Telegram action without silently sending anything."""
    attachments = attachments or []
    recipient_clean = re.sub(r"[^A-Za-z0-9_@+.-]+", "", recipient or "").strip()
    username = recipient_clean.lstrip("@") if recipient_clean.startswith("@") else ""
    open_url = f"https://t.me/{username}" if username else ""
    payload = {
        "recipient": recipient_clean,
        "message": message,
        "attachments": attachments,
        "open_url": open_url,
        "next_steps": [
            "Открыть Telegram Desktop/Web или ссылку t.me, если указан username.",
            "Вставить подготовленный текст и приложить файлы.",
            "Показать пользователю финальный текст перед отправкой.",
            "Отправить только после явного подтверждения.",
        ],
    }
    out = ensure_stella_dir(root) / "telegram_action.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    append_operator_log(root, "telegram_action_prepared", {"recipient": recipient_clean, "attachments": attachments, "file": str(out)})
    return {"ok": True, "file": str(out), **payload}


def home_assistant_call(root: Path, base_url: str, token_env: str, domain: str, service: str, entity_id: str = "", data: dict[str, Any] | None = None, dry_run: bool = True) -> dict[str, Any]:
    """Prepare or execute a Home Assistant service call using token from an environment variable."""
    data = data or {}
    base_url = (base_url or os.getenv("HOME_ASSISTANT_URL", "")).rstrip("/")
    token_env = token_env or "HOME_ASSISTANT_TOKEN"
    token = os.getenv(token_env, "")
    domain = re.sub(r"[^a-zA-Z0-9_]+", "", domain or "")
    service = re.sub(r"[^a-zA-Z0-9_]+", "", service or "")
    payload: dict[str, Any] = dict(data)
    if entity_id:
        payload["entity_id"] = entity_id
    plan = {"base_url": base_url, "token_env": token_env, "domain": domain, "service": service, "payload": redact(payload), "dry_run": dry_run}
    if dry_run:
        append_operator_log(root, "home_assistant_dry_run", plan)
        return {"ok": True, "planned": plan, "message": "Dry-run: реальный вызов не выполнен."}
    if not base_url or not token:
        return {"ok": False, "error": "Нужны HOME_ASSISTANT_URL и токен в переменной окружения, например HOME_ASSISTANT_TOKEN."}
    if not domain or not service:
        return {"ok": False, "error": "Нужны domain и service."}
    response = requests.post(f"{base_url}/api/services/{domain}/{service}", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json=payload, timeout=30)
    append_operator_log(root, "home_assistant_call", {"planned": plan, "status_code": response.status_code, "response": response.text[:2000]})
    return {"ok": response.status_code < 400, "status_code": response.status_code, "response": response.text[:4000]}
