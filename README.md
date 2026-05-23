# Stella AI Agent 3.8 Enterprise Autopilot Edition

**Stella AI Agent 3.8 Enterprise Autopilot Edition** — это локальный терминальный AI-агент для разработки, DevOps, проверки веб-интерфейсов, GUI-автоматизации, безопасного тестирования ботов и операторских задач. Stella работает через цикл инструментов: модель не делает вид, что «сама видит» файловую систему, а вызывает конкретные действия, получает результат, анализирует его и продолжает задачу до завершения.

> Stella является самостоятельным AI coding agent. Проект не копирует закрытые интерфейсы, приватные промпты или proprietary-поведение сторонних продуктов; он предоставляет собственный CLI, системный промпт, approval-модель, набор инструментов и JSONL-журнал совместимости.

## Быстрая установка

На Windows открой PowerShell и выполни команду ниже. Установщик скачает все Enterprise-модули, создаст виртуальное окружение, поставит Python-зависимости, создаст `stella.cmd` и `stella.ps1`, а затем добавит Stella в пользовательский `PATH`.

```powershell
irm https://raw.githubusercontent.com/a1x10/stella-ai-coder/main/install.ps1 | iex
```

На Linux или macOS можно использовать shell-установщик. Он скачивает те же модули, создаёт launcher `stella`, предупреждает про отсутствующие `python3-tk`, `adb`, `git` или `npm`, а также пытается подготовить локальную Ollama-модель, если Ollama установлена.

```bash
curl -fsSL https://raw.githubusercontent.com/a1x10/stella-ai-coder/main/install.sh | bash
```

После установки открой новый терминал и запусти `stella`. Для разработки из исходников достаточно создать виртуальное окружение и установить зависимости из `requirements.txt`.

| Платформа | Команда запуска | Примечание |
|---|---|---|
| Windows | `stella` или `stella.ps1` | Если PowerShell блокирует скрипты, запускай `stella.cmd`. |
| Linux/macOS | `stella` | Если Tkinter недоступен, статус-окно автоматически отключится. |
| Из исходников | `python stella_ai_coder.py` | Запускать из корня проекта после `pip install -r requirements.txt`. |

## Провайдеры и модели

По умолчанию Stella использует **Ollama** и модель `qwen2.5-coder:1.5b`, чтобы запускаться локально даже на относительно слабых машинах. Провайдер, модель и approval-режим меняются через переменные окружения.

| Переменная | Пример | Назначение |
|---|---|---|
| `STELLA_PROVIDER` | `ollama` | Выбирает провайдера модели. |
| `STELLA_MODEL` | `qwen2.5-coder:7b` | Выбирает конкретную модель. |
| `STELLA_OLLAMA_URL` | `http://localhost:11434` | Меняет адрес Ollama API. |
| `STELLA_APPROVAL_MODE` | `suggest`, `auto`, `readonly` | Управляет подтверждением рискованных инструментов. |
| `STELLA_SKIP_PIXEL_PROMPT` | `1` | Отключает one-time подсказку Pixel Agents при первом запуске. |

## Возможности Enterprise Edition

Stella 3.8 Enterprise Autopilot Edition расширена набором инструментов, который закрывает не только coding workflow, но и deploy, визуальную проверку, Android/phone control, тестирование ботов, multi-agent planning, браузерное исследование, GitHub/source scanning, operator log и подготовку сообщений/отчётов.

| Возможность | Статус | Детали |
|---|---:|---|
| Чтение, поиск, запись и patch файлов | Готово | Работа ограничена активным project root, опасные действия подтверждаются. |
| Shell и Git | Готово | Команды, diff, status, branch, checkout и commit доступны через инструменты. |
| SSH/Deploy | Готово | `ssh_run` выполняет удалённые команды; `deploy_app` поддерживает локальные deploy-команды и удалённый deploy через SSH. |
| Style-Guide AI | Готово | `analyze_style` анализирует `.editorconfig`, ESLint/Prettier, `pyproject.toml`, `package.json`, Git-файлы и создаёт `.stella_style`. |
| Multi-agent planning | Готово | `spawn_agents` запускает мини-агентов последовательно, ведёт общий контекст и сохраняет summary в `.stella/agents_shared_context.md`. |
| Bot Sandbox | Готово | `bot_sandbox` и `stella_bot_sandbox.py` симулируют Telegram/WhatsApp-диалоги без реальных токенов и телефонов. |
| Visual QA | Готово | `visual_qa` открывает URL, делает скриншот и возвращает метаданные/базовые smoke-checks. |
| GUI automation | Готово | Мышь, клавиатура, hotkeys и screenshot через `pyautogui` с fail-safe поведением. |
| Desktop Operator | Готово | `desktop_*` инструменты видят экран через screenshot/OCR, запускают приложения, находят окна, фокусируют их, кликают, печатают, нажимают hotkeys и пишут действия в operator log. |
| Android/phone control | Готово | `phone_*` инструменты управляют Android через `adb`: tap, swipe, text, keyevent, shell, screenshot. |
| Auto-Pentest smoke checks | Готово | `security_scan` содержит быстрые эвристические SQLi/XSS-проверки для разрешённых тестовых целей. |
| Pixel Agents bridge | Готово | Stella пишет Claude-style JSONL в `~/.claude/projects`, умеет подготовить Pixel Agents через VS Code/source path и создаёт live-viewer действий. |
| Autopilot planning | Готово | `autopilot_plan` разбивает сложную задачу на этапы, классифицирует риск и предлагает research/agent/approval workflow. |
| Research и GitHub scanner | Готово | `autopilot_research` ищет и сохраняет источники; `github_scan` читает публичный GitHub через API без запуска чужого кода. |
| Reports и Telegram draft | Готово | `draft_report` и `telegram_action` готовят отчёт, текст сообщения, вложения и ссылку `t.me`, но не отправляют скрыто. |
| Server/Home connectors | Готово | `connector_profile` хранит профили серверов/API; `home_assistant_action` работает в dry-run или выполняет service call через токен из env после подтверждения. |
| Operator live log | Готово | Все Autopilot-действия пишутся в `.stella/operator_actions.jsonl`, а `live_actions_viewer` создаёт `.stella/live_actions.html`. |

## Команды внутри Stella

Команды начинаются с `/`, а обычный текст считается задачей для агента. В интерактивном режиме можно попросить Stella изменить проект, проверить баг, провести локальный деплой или протестировать бот-сценарий.

| Команда | Назначение |
|---|---|
| `/help` или `/помощь` | Показывает команды и доступные инструменты. |
| `/status` | Показывает провайдера, модель, project root, approval-режим и файл сессии. |
| `/root PATH` или `/папка PATH` | Меняет активную папку проекта. |
| `/approval suggest` | Спрашивать подтверждение перед рискованными действиями. |
| `/approval auto` | Выполнять инструменты без подтверждений; использовать только в доверенных проектах. |
| `/approval readonly` | Запретить запись файлов и shell-команды. |
| `/plan` | Показать текущий план Stella. |
| `/tools` | Показать группы инструментов. |
| `/pixel` | Показать статус Pixel Agents bridge, путь JSONL-журнала и live-viewer. |
| `/doctor` или `/доктор` | Запустить диагностику окружения. |
| `/clear` или `/очистить` | Очистить контекст диалога. |
| `/exit` или `/выход` | Выйти из Stella. |

## Bot Sandbox

`stella_bot_sandbox.py` — отдельный локальный эмулятор Telegram/WhatsApp-ботов. Он не отправляет реальные сообщения и не требует токенов. Sandbox умеет запускать JSON-сценарии, слать simulated updates на webhook, подключать in-process handler в формате `module:function`, проводить load-test и писать transcript в JSONL.

```bash
python stella_bot_sandbox.py --platform telegram
python stella_bot_sandbox.py --scenario scenario.json --handler my_bot:on_update
python stella_bot_sandbox.py --webhook http://127.0.0.1:8000/webhook --load --users 50 --messages-per-user 3
```

Изнутри Stella доступен инструмент `bot_sandbox(platform="telegram", scenario={...}, handler="", webhook_url="")`. Если используется webhook, Stella запрашивает подтверждение, потому что это сетевое действие.

## Autopilot / Operator mode

Autopilot-режим создан для задач вида: «изучи сайт, пойми как сделать, собери приложение, подготовь отчёт и отправь начальнику». Stella сначала строит план, затем ищет информацию, читает источники, при необходимости сканирует GitHub, создаёт код/документы и ведёт прозрачный журнал действий. Если задача сложная или кажется невозможной, Stella должна сначала провести исследование и предложить практический маршрут, а не останавливаться на слове «невозможно».

| Инструмент | Что делает | Ограничение безопасности |
|---|---|---|
| `autopilot_plan` | Делит большую задачу на этапы, research, build, QA и delivery. | Реальное выполнение опасных шагов требует approval. |
| `autopilot_research` | Ищет источники и сохраняет `.stella/research_notes.json`. | Не запускает найденный код автоматически. |
| `github_scan` | Читает дерево публичного GitHub-репозитория, README и выбранные файлы. | Использует API/HTTP и не исполняет содержимое репозитория. |
| `telegram_action` | Готовит текст, вложения и ссылку на Telegram username. | Финальная отправка сообщения делается только после явного подтверждения. |
| `home_assistant_action` | Готовит или выполняет Home Assistant service call. | По умолчанию `dry_run=true`; реальное действие требует token env и approval. |
| `live_actions_viewer` | Создаёт HTML-страницу для просмотра operator log и Pixel JSONL. | Viewer показывает журнал, но не даёт скрытого remote-control. |

## Desktop Operator: управление компьютером и приложениями

Desktop Operator добавляет Stella слой управления интерактивным рабочим столом. Он предназначен для задач вида: «открой приложение», «посмотри, что на экране», «нажми кнопку», «заполни форму», «переключись в окно», «сделай скриншот», «найди текст на экране» или «управляй установленной программой по шагам». Для реального управления нужен разблокированный desktop-сеанс; в headless/серверной среде инструменты корректно возвращают диагностическую ошибку, не ломая импорт Stella.

| Инструмент | Назначение |
|---|---|
| `desktop_env` | Проверяет ОС, DISPLAY/Wayland, доступность `pyautogui`, OCR, `wmctrl`, `xdotool` и других backend-компонентов. |
| `desktop_screenshot` | Делает скриншот экрана и сохраняет его в `.stella/screenshots`. |
| `desktop_ocr` | Распознаёт текст на скриншоте через Tesseract OCR, если он установлен. |
| `desktop_windows` | Показывает список видимых окон через `pygetwindow`, `wmctrl` или системные fallback-команды. |
| `desktop_focus_window` | Переключает фокус на окно по заголовку или индексу. |
| `desktop_open_app` | Запускает приложение или команду через системный launcher. |
| `desktop_click`, `desktop_type`, `desktop_hotkey`, `desktop_press`, `desktop_scroll` | Выполняют базовые действия мыши и клавиатуры. |

На Linux для лучшего управления окнами рекомендуется установить `wmctrl`, `xdotool` и Tesseract: `sudo apt install wmctrl xdotool tesseract-ocr tesseract-ocr-eng tesseract-ocr-rus`. На Windows Desktop Operator работает в интерактивной пользовательской сессии; OCR требует установленный Tesseract в `PATH`. Все действия записываются в `.stella/operator_actions.jsonl`, а `live_actions_viewer` позволяет открыть HTML-наблюдение за выполнением.

> Stella не должна скрыто покупать подписки, создавать аккаунты, отправлять сообщения, вводить пароли, удалять важные данные или управлять устройствами без подтверждения. Она может подготовить шаги, открыть нужные окна и выполнить действие после явного подтверждения пользователя, чтобы сохранить прозрачность и не подставить владельца компьютера.

## Pixel Agents integration

Pixel Agents в публичном README описывает основной пользовательский путь через VS Code extension и исходную установку командой `git clone`, `npm install`, `cd webview-ui && npm install`, `npm run build`.[1] Stella поэтому реализует **двойной безопасный workflow**: она всегда пишет совместимый JSONL-журнал, а `/pixel` может открыть проект в VS Code или, с согласия пользователя, клонировать и собрать исходники Pixel Agents в `~/.stella-ai-coder/pixel-agents`.

```text
~/.claude/projects/stella-<project>-<hash>/stella-<timestamp>.jsonl
```

Первый запуск показывает one-time подсказку Pixel Agents. Маркер хранится в `~/.stella-ai-coder/.pixel_first_run_checked`; если подсказка не нужна, установи `STELLA_SKIP_PIXEL_PROMPT=1`.

## Безопасность

У Stella есть три approval-режима. В режиме **suggest** read-only действия выполняются сразу, а операции записи, shell, browser/app open, webhook, SSH, deploy, phone-control и desktop-control требуют подтверждения. В режиме **auto** агент действует быстрее, но этот режим безопасен только в доверенных проектах и при включённом наблюдении за логом. В режиме **readonly** Stella может изучать проект, но не может писать файлы и выполнять команды.

> Сильный терминальный агент способен менять файлы, запускать команды, открывать браузер, взаимодействовать с GUI и отправлять запросы на локальные или удалённые сервисы. Поэтому Stella отделяет рассуждение модели от реального исполнения через явные инструменты, project-root ограничения и approval checks.

## Разработка и проверка

```bash
git clone https://github.com/a1x10/stella-ai-coder.git
cd stella-ai-coder
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m py_compile stella_ai_coder.py stella_autopilot_tools.py stella_bot_sandbox.py stella_gui_tools.py stella_status_window.py stella_security_tools.py
python stella_ai_coder.py --version
```

На Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python .\stella_ai_coder.py --version
```

## Публикация обновлений

Если есть права на репозиторий, изменения публикуются стандартным Git workflow. Перед публикацией желательно проверить синтаксис всех Python-файлов и убедиться, что установщики скачивают все обязательные модули.

```bash
git status
git add stella_ai_coder.py stella_autopilot_tools.py stella_gui_tools.py stella_status_window.py stella_security_tools.py stella_bot_sandbox.py README.md PIXEL_AGENTS.md requirements.txt install.ps1 install.sh
git commit -m "Release Stella AI Agent 3.8 Enterprise Autopilot Edition"
git push
```

## References

[1]: https://github.com/pixel-agents-hq/pixel-agents "GitHub — pixel-agents-hq/pixel-agents"
