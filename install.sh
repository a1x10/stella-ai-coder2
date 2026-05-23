#!/usr/bin/env bash
set -euo pipefail

REPO_RAW="${STELLA_REPO_RAW:-https://raw.githubusercontent.com/a1x10/stella-ai-coder/main}"
INSTALL_DIR="${STELLA_INSTALL_DIR:-$HOME/.stella-ai-coder}"
VENV_DIR="$INSTALL_DIR/.venv"
AGENT_FILE="$INSTALL_DIR/stella_ai_coder.py"
REQ_FILE="$INSTALL_DIR/requirements.txt"
LAUNCHER="$INSTALL_DIR/stella"
MODEL="${STELLA_MODEL:-qwen2.5-coder:1.5b}"

printf '\n\033[36m=== Stella AI Agent 3.8 Enterprise Autopilot installer ===\033[0m\n'
printf 'Install dir: %s\n' "$INSTALL_DIR"
printf 'Model: %s\n\n' "$MODEL"

command_exists() { command -v "$1" >/dev/null 2>&1; }

mkdir -p "$INSTALL_DIR"

if ! command_exists python3; then
  printf '\033[31mPython 3 was not found. Install Python 3.10+ and run again.\033[0m\n' >&2
  exit 1
fi

if ! command_exists curl; then
  printf '\033[31mcurl was not found. Install curl and run again.\033[0m\n' >&2
  exit 1
fi

printf '\033[36mDownloading Stella files\033[0m\n'
for file in \
  stella_ai_coder.py \
  stella_autopilot_tools.py \
  stella_desktop_operator.py \
  stella_gui_tools.py \
  stella_status_window.py \
  stella_security_tools.py \
  stella_bot_sandbox.py \
  requirements.txt \
  README.md \
  PIXEL_AGENTS.md; do
  curl -fsSL "$REPO_RAW/$file" -o "$INSTALL_DIR/$file" || {
    if [ "$file" = "PIXEL_AGENTS.md" ] || [ "$file" = "README.md" ]; then
      printf '\033[33mOptional file %s was not downloaded.\033[0m\n' "$file"
    else
      printf '\033[31mFailed to download required file: %s\033[0m\n' "$file" >&2
      exit 1
    fi
  }
done

if [ ! -x "$VENV_DIR/bin/python" ]; then
  printf '\033[36mCreating Python virtual environment\033[0m\n'
  python3 -m venv "$VENV_DIR"
fi

printf '\033[36mInstalling Python packages\033[0m\n'
"$VENV_DIR/bin/python" -m pip install -U pip
"$VENV_DIR/bin/python" -m pip install -r "$REQ_FILE"

if ! "$VENV_DIR/bin/python" - <<'PY' >/dev/null 2>&1
import tkinter
PY
then
  printf '\033[33mTkinter is not available. On Debian/Ubuntu install it with: sudo apt install python3-tk\033[0m\n'
fi

if ! command_exists adb; then
  printf '\033[33madb was not found. Phone-control tools will work after installing Android platform-tools.\033[0m\n'
fi

if ! command_exists wmctrl || ! command_exists xdotool; then
  printf '\033[33mDesktop Operator on Linux works best with wmctrl and xdotool: sudo apt install wmctrl xdotool\033[0m\n'
fi

if ! command_exists tesseract; then
  printf '\033[33mScreen OCR needs Tesseract OCR: sudo apt install tesseract-ocr tesseract-ocr-eng tesseract-ocr-rus\033[0m\n'
fi

if ! command_exists git || ! command_exists npm; then
  printf '\033[33mGit and npm are recommended for optional Pixel Agents source setup.\033[0m\n'
fi

if ! command_exists ollama; then
  printf '\033[33mOllama was not found. Install it from https://ollama.com/download if you want local models.\033[0m\n'
else
  if ! curl -fsS http://localhost:11434/api/tags >/dev/null 2>&1; then
    printf '\033[36mStarting Ollama in background\033[0m\n'
    (ollama serve >/tmp/stella-ollama.log 2>&1 &)
    sleep 5
  fi
  printf '\033[36mPulling model: %s\033[0m\n' "$MODEL"
  ollama pull "$MODEL" || true
fi

cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
export STELLA_MODEL="${MODEL}"
exec "${VENV_DIR}/bin/python" "${AGENT_FILE}" "\$@"
EOF
chmod +x "$LAUNCHER"

case ":$PATH:" in
  *":$INSTALL_DIR:"*) ;;
  *)
    SHELL_RC=""
    if [ -n "${ZSH_VERSION:-}" ]; then SHELL_RC="$HOME/.zshrc"; else SHELL_RC="$HOME/.bashrc"; fi
    printf '\n# Stella AI Agent\nexport PATH="%s:$PATH"\n' "$INSTALL_DIR" >> "$SHELL_RC"
    printf '\033[32mAdded Stella to PATH in %s. Open a new terminal or run: export PATH="%s:$PATH"\033[0m\n' "$SHELL_RC" "$INSTALL_DIR"
    ;;
esac

printf '\n\033[32mStella Enterprise Autopilot + Desktop Operator is installed.\033[0m\n'
printf 'Run: %s/stella\n' "$INSTALL_DIR"
printf 'Or open a new terminal and run: stella\n\n'
"$LAUNCHER" --version
