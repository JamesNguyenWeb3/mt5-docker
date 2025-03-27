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

# Setup ZeroMQ for MT5
setup_zmq() {
    log "Setting up ZeroMQ for MetaTrader 5..."
    # Make the setup script executable
    chmod +x /setup_zmq.sh
    # Run the setup script
    /setup_zmq.sh
    log "ZeroMQ setup completed"
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
    setup-zmq)
        setup_zmq
        ;;
    *)
        exec "$@"
        ;;
esac 