#!/bin/bash
# Script to run the Python ZeroMQ client

# Default values
ZMQ_ADDRESS="tcp://localhost:5555"
SYMBOLS=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --address)
      ZMQ_ADDRESS="$2"
      shift 2
      ;;
    --symbols)
      shift
      while [[ $# -gt 0 && ! $1 == --* ]]; do
        SYMBOLS="$SYMBOLS $1"
        shift
      done
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--address tcp://host:port] [--symbols symbol1 symbol2 ...]"
      exit 1
      ;;
  esac
done

# Build the command
if [ -z "$SYMBOLS" ]; then
  CMD="python3 receive_ticks.py --address $ZMQ_ADDRESS"
else
  CMD="python3 receive_ticks.py --address $ZMQ_ADDRESS --symbols $SYMBOLS"
fi

# Run the client
echo "Starting MT5 tick client with: $CMD"
$CMD 