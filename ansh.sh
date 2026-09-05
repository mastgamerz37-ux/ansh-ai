#!/bin/bash

show_help() {
    echo ""
    echo "========================================="
    echo "        ANSH AI COMMAND LINE TOOL"
    echo "========================================="
    echo "Usage: "
    echo "  ./ansh.sh install   - Automatically sets up Python venv and installs all dependencies"
    echo "  ./ansh.sh dev       - Starts Ansh with console output (like npm run dev)"
    echo "  ./ansh.sh start     - Starts Ansh silently in the background"
    echo "========================================="
    echo ""
}

install() {
    echo "[ANSH] Checking Python..."
    if ! command -v python3 &> /dev/null; then
        echo "[ANSH] Python3 is missing! Please install Python 3.10+ manually."
        exit 1
    fi

    echo "[ANSH] Creating Environment..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi

    echo "[ANSH] Installing Dependencies..."
    source venv/bin/activate
    python3 -m pip install --upgrade pip --quiet
    pip install -r requirements.txt
    echo "[ANSH] Install Complete! Starting Ansh..."
    start_ansh
}

dev() {
    echo "[ANSH] Starting Developer Mode..."
    if [ ! -d "venv" ]; then
        echo "[ANSH] Environment not found! Run \"./ansh.sh install\" first."
        exit 1
    fi
    source venv/bin/activate
    python3 main.py
}

start_ansh() {
    echo "[ANSH] Starting Ansh AI in background..."
    if [ ! -d "venv" ]; then
        echo "[ANSH] Environment not found! Run \"./ansh.sh install\" first."
        exit 1
    fi
    source venv/bin/activate
    
    # Run silently in background (nohup)
    nohup python3 main.py > /dev/null 2>&1 &
    
    echo "[ANSH] Ansh is now running in the background (PID: $!)."
}

case "$1" in
    install)
        install
        ;;
    dev)
        dev
        ;;
    start)
        start_ansh
        ;;
    *)
        show_help
        ;;
esac
