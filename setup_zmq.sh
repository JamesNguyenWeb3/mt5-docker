#!/bin/bash
# Script to set up ZeroMQ for MetaTrader 5 in Docker

# Create required directories
echo "Creating required directories..."
mkdir -p /mt5_zmq_setup

# Download libzmq DLL for Windows
echo "Downloading ZeroMQ Windows DLL..."
cd /mt5_zmq_setup
wget -q https://github.com/zeromq/libzmq/releases/download/v4.3.2/zeromq-4.3.2-windows.zip
unzip -q zeromq-4.3.2-windows.zip

# Helper function to copy files to the MT5 install directory in Wine
function copy_to_mt5() {
  local src="$1"
  local dest="$2"
  echo "Copying $src to $dest"
  su - trader -c "mkdir -p '$(dirname "$dest")'"
  su - trader -c "cp '$src' '$dest'"
}

# Copy ZeroMQ DLL to MT5 installation
echo "Copying ZeroMQ DLL to MT5 installation..."
WINE_SYSTEM32="~/.wine/drive_c/windows/system32"
MT5_INCLUDE_DIR="~/.wine/drive_c/Users/trader/AppData/Roaming/MetaQuotes/Terminal/Common/Files/Include/ZMQ"

# Copy required DLLs 
copy_to_mt5 "/mt5_zmq_setup/bin/libzmq-v120-mt-4_3_2.dll" "$WINE_SYSTEM32/libzmq.dll"

# Create ZMQ directory in MT5 Include directory
su - trader -c "mkdir -p '$MT5_INCLUDE_DIR'"

# Copy MQL5 ZeroMQ files
echo "Copying MQL5 ZeroMQ files to MT5 installation..."
copy_to_mt5 "/mql5/Include/ZMQ/ZmqSocket.mqh" "$MT5_INCLUDE_DIR/ZmqSocket.mqh" 
copy_to_mt5 "/mql5/Include/ZMQ/ZmqHelper.mqh" "$MT5_INCLUDE_DIR/ZmqHelper.mqh"
copy_to_mt5 "/mql5/Experts/ZmqTickStreamer.mq5" "$MT5_INCLUDE_DIR/../Experts/ZmqTickStreamer.mq5"

# Clean up
echo "Cleaning up temporary files..."
rm -rf /mt5_zmq_setup

echo "ZeroMQ setup for MetaTrader 5 completed successfully!" 