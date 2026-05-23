# STELLA AI AGENT 3.7 ENTERPRISE — ИНСТРУКЦИЯ ПО ПЕРЕДАЧЕ

**Цель:** Достроить Stella AI Agent 3.7 Enterprise Edition до полного функционала, заменяющего Claude Code, с мультиагентностью, управлением GUI и продвинутыми Enterprise-инструментами.

## ЧТО УЖЕ СДЕЛАНО:
1.  **Ядро агента (stella_ai_coder.py):**
    *   Реализован CLI-интерфейс на `rich`.
    *   Поддержка Ollama (локально) и OpenAI (API).
    *   Система инструментов (File, Shell, Git, Web).
    *   **Pixel Agents Integration:** Генерация совместимых JSONL-транскриптов в `~/.claude/projects/`.
    *   **Мультиагентность (Swarm):** Реализован инструмент `spawn_agents` для параллельного запуска мини-агентов.
    *   **Система подтверждений:** Режимы `ask`, `auto`, `readonly`.

2.  **GUI Управление (stella_gui_tools.py):**
    *   Интеграция `pyautogui` для мыши, клавиатуры и скриншотов.
    *   Инструменты: `move_mouse`, `click`, `type_text`, `press_key`, `hotkey`, `screenshot`, `get_screen_resolution`.

3.  **Статус-окно (stella_status_window.py):**
    *   Реализовано всплывающее окно на `Tkinter` с надписью "Stella AI работает...", которое висит поверх всех окон во время работы агента.

4.  **Безопасность (stella_security_tools.py):**
    *   Реализован инструмент `security_scan` для базового Auto-Pentest (SQLi, XSS).

5.  **Visual QA:**
    *   Интегрирован инструмент `visual_qa` (открыть URL + скриншот).

## ЧТО НУЖНО ДОДЕЛАТЬ (ЗАДАЧИ ДЛЯ ТЕБЯ):

### 1. SSH-администрирование и Деплой
*   Добавить инструмент `ssh_run(host, user, command)` для удаленного управления серверами.
*   Добавить инструмент `deploy_app(config)` для автоматической настройки Docker/Nginx по шаблонам.

### 2. Bot Sandbox (Эмулятор мессенджеров)
*   Создать файл `stella_bot_sandbox.py`.
*   Реализовать эмулятор, который симулирует входящие сообщения для Telegram/WhatsApp ботов, чтобы Стелла могла тестировать логику ботов локально без реального API.

### 3. Самообучение (Style-Guide AI)
*   Добавить инструмент `analyze_style(path)`, который читает `.editorconfig`, `.eslintrc` или историю Git и создает файл `.stella_style`, которому агент будет следовать при написании кода.

### 4. Улучшение Мультиагентности
*   Сделать так, чтобы `spawn_agents` могли обмениваться данными через общую "память" (shared context file).

### 5. Финальная упаковка
*   Обновить `README.md` и `PIXEL_AGENTS.md` со всеми новыми функциями.
*   Обновить установщики `install.ps1` и `install.sh`, чтобы они ставили все зависимости (`pyautogui`, `python3-tk` и т.д.).

## ФАЙЛЫ В ПРОЕКТЕ:
*   `stella_ai_coder.py` — основной файл.
*   `stella_gui_tools.py` — управление ПК.
*   `stella_status_window.py` — GUI окно статуса.
*   `stella_security_tools.py` — Auto-Pentest.
*   `requirements.txt` — зависимости.
*   `install.ps1` / `install.sh` — установщики.

**Бро, доделай это без сжатия, максимально качественно. От этого зависит карьера человека!**
