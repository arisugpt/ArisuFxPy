#!/usr/bin/env bash

set -e

echo "=========================================="
echo "    ArisuFxPy Auto Installer & Verifier   "
echo "=========================================="

# Command existence check helper
has_cmd() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Environment Detection & Python Check / Install / Update
if [ -n "$TERMUX_VERSION" ] || [ -d "/data/data/com.termux" ]; then
    echo "[*] Environment: Termux detected (Android)"
    pkg update -y

    # Check if Python exists in Termux
    if has_cmd python || has_cmd python3; then
        echo "[âœ”] Python already installed. Updating Python package..."
        pkg install --upgrade python -y 2>/dev/null || pkg install python -y
    else
        echo "[!] Python not found. Installing Python..."
        pkg install python -y
    fi

    echo "[*] Ensuring build tools (git, clang, make) are installed..."
    pkg install git clang make -y
    PYTHON_BIN="python"

elif has_cmd apt-get; then
    echo "[*] Environment: Debian / Ubuntu Linux PC detected"
    
    SUDO=""
    if [ "$EUID" -ne 0 ] && has_cmd sudo; then
        SUDO="sudo"
    fi

    $SUDO apt-get update -y

    # Check if Python3 exists in Debian/Ubuntu
    if has_cmd python3; then
        echo "[âœ”] Python3 already installed. Upgrading Python3..."
        $SUDO apt-get install --only-upgrade -y python3 python3-pip python3-dev 2>/dev/null || true
    else
        echo "[!] Python3 not found. Installing Python3 & pip..."
        $SUDO apt-get install -y python3 python3-pip python3-dev
    fi

    $SUDO apt-get install -y git build-essential
    PYTHON_BIN="python3"

elif has_cmd pacman; then
    echo "[*] Environment: Arch Linux PC detected"
    
    SUDO=""
    if [ "$EUID" -ne 0 ] && has_cmd sudo; then
        SUDO="sudo"
    fi

    $SUDO pacman -Sy --noconfirm

    if has_cmd python; then
        echo "[âœ”] Python already installed. Updating..."
        $SUDO pacman -S --noconfirm python python-pip
    else
        echo "[!] Python not found. Installing..."
        $SUDO pacman -S --noconfirm python python-pip
    fi

    $SUDO pacman -S --needed --noconfirm git base-devel
    PYTHON_BIN="python"

elif has_cmd brew; then
    echo "[*] Environment: macOS (Homebrew) detected"
    
    if has_cmd python3; then
        echo "[âœ”] Python already installed. Upgrading..."
        brew upgrade python 2>/dev/null || true
    else
        echo "[!] Python not found. Installing..."
        brew install python
    fi

    brew install git
    PYTHON_BIN="python3"

else
    echo "[!] Unknown package manager."
    if has_cmd python3; then
        PYTHON_BIN="python3"
    elif has_cmd python; then
        PYTHON_BIN="python"
    else
        echo "[âœ–] Python not found in system or auto-install not supported. Please install Python manually."
        exit 1
    fi
fi

# 2. Pip Upgrade & Package Installation
echo ""
echo "[*] Upgrading pip..."
$PYTHON_BIN -m pip install --upgrade pip 2>/dev/null || true

echo ""
echo "[*] Installing dependencies (tabulate)..."
$PYTHON_BIN -m pip install tabulate 2>/dev/null || \
$PYTHON_BIN -m pip install --break-system-packages tabulate 2>/dev/null || true

echo ""
echo "[*] Installing / Updating ArisuFxPy from GitHub..."
$PYTHON_BIN -m pip install git+https://github.com/arisugpt/ArisuFxPy.git 2>/dev/null || \
$PYTHON_BIN -m pip install --break-system-packages git+https://github.com/arisugpt/ArisuFxPy.git

# 3. Verification & Exact Path Print
echo ""
echo "[*] Verifying package installation..."

if $PYTHON_BIN -c "import ArisuFxPy" 2>/dev/null; then
    INSTALL_PATH=$($PYTHON_BIN -c "import ArisuFxPy; print(getattr(ArisuFxPy, '__file__', 'Module installed as namespace/binary'))")
    VERSION=$($PYTHON_BIN -c "import ArisuFxPy; print(getattr(ArisuFxPy, '__version__', 'unknown'))")
    echo "=========================================="
    echo "[âœ”] Success: ArisuFxPy installed and verified!"
    echo "[*] Version       : $VERSION"
    echo "[*] Python Binary : $(command -v $PYTHON_BIN)"
    echo "[*] Module Path   : $INSTALL_PATH"
    echo "=========================================="
else
    echo "=========================================="
    echo "[âœ–] Error: Module import failed!"
    echo "=========================================="
    exit 1
fi