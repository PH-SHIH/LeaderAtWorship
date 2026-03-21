#!/bin/bash
# LeaderAtWorship — One-click Setup Script (macOS Apple Silicon)
set -e

echo "========================================="
echo "  LeaderAtWorship — 一鍵安裝"
echo "========================================="
echo ""

# ── 1. Check macOS ────────────────────────────
if [[ "$(uname)" != "Darwin" ]]; then
    echo "[!] This tool is designed for macOS Apple Silicon."
    exit 1
fi

# ── 2. Homebrew ───────────────────────────────
if ! command -v brew &>/dev/null; then
    echo "[*] Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    echo "[OK] Homebrew"
fi

# ── 3. System Dependencies ───────────────────
echo ""
echo "[*] Installing system dependencies..."

# ffmpeg (required for audio processing)
if ! command -v ffmpeg &>/dev/null; then
    echo "  -> ffmpeg"
    brew install ffmpeg
else
    echo "[OK] ffmpeg"
fi

# Python 3.10+ (via Homebrew if system python is too old)
PYTHON_CMD=""
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
    if [[ "$PY_MAJOR" -ge 3 && "$PY_MINOR" -ge 10 ]]; then
        PYTHON_CMD="python3"
        echo "[OK] Python $PY_VER"
    fi
fi

if [[ -z "$PYTHON_CMD" ]]; then
    echo "  -> Python 3.12"
    brew install python@3.12
    PYTHON_CMD="python3.12"
fi

# ── 4. Virtual Environment ───────────────────
echo ""
VENV_DIR=".venv"
if [[ ! -d "$VENV_DIR" ]]; then
    echo "[*] Creating virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR"
else
    echo "[OK] Virtual environment exists"
fi

# Activate
source "$VENV_DIR/bin/activate"
echo "[OK] Activated: $(python3 --version)"

# ── 5. Python Dependencies ───────────────────
echo ""
echo "[*] Installing Python dependencies..."
python3 -m pip install --upgrade pip -q
python3 -m pip install -e ".[ml,dev]" -q
echo "[OK] All Python packages installed"

# ── 6. Environment Config ────────────────────
echo ""
if [[ ! -f ".env" ]]; then
    echo "[*] Creating .env from template..."
    cp .env.example .env
    echo "[OK] .env created (edit if needed)"
else
    echo "[OK] .env exists"
fi

# ── 7. Database Setup ────────────────────────
echo ""
echo "[*] Setting up database..."
mkdir -p data/db data/audio data/exports data/models
python3 -m alembic upgrade head
echo "[OK] Database ready"

# ── 8. Summary ───────────────────────────────
echo ""
echo "========================================="
echo "  Installation Complete!"
echo "========================================="
echo ""
echo "  Start the server:"
echo "    source .venv/bin/activate"
echo "    uvicorn app.main:app --reload --port 8000"
echo ""
echo "  Then open: http://localhost:8000"
echo ""
echo "========================================="
