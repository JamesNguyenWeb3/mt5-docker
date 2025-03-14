#!/bin/bash
set -e

# Function to log messages
log() {
    echo "[$(date +%Y-%m-%d\ %H:%M:%S)] $1"
}

# Install MetaTrader 5
install_mt5() {
    log "Starting MetaTrader 5 installation..."
    su - trader -c "/home/trader/install_mt5.sh"
    log "MetaTrader 5 installation completed (or was terminated by user)"
}

# Start MetaTrader 5
start_mt5() {
    log "Starting MetaTrader 5 application..."
    su - trader -c "/home/trader/start_mt5.sh"
}

# Start VNC server
start_vnc() {
    log "Starting VNC server..."
    su - trader -c "/home/trader/start_vnc.sh"
    log "VNC server started on port 5900"
    tail -f /dev/null
}

# Main logic
case "$1" in
    install)
        install_mt5
        ;;
    start)
        start_mt5
        ;;
    vnc)
        start_vnc
        ;;
    *)
        exec "$@"
        ;;
esac 