#!/usr/bin/env python
"""
ZeroMQ Client for MetaTrader 5 Real-time Tick Data
=================================================

This script connects to a MetaTrader 5 ZeroMQ publisher and
receives real-time tick data. The data can be processed, stored,
or forwarded to other systems as needed.
"""

import sys
import json
import signal
import zmq
import time
import pandas as pd
from datetime import datetime
import threading
from typing import Dict, List, Optional, Union

class MT5TickSubscriber:
    """Client for subscribing to MetaTrader 5 tick data via ZeroMQ"""
    
    def __init__(self, zmq_address: str = "tcp://localhost:5555", symbols: Optional[List[str]] = None) -> None:
        """
        Initialize the MT5 tick subscriber.
        
        Args:
            zmq_address: ZeroMQ address to connect to
            symbols: List of symbols to subscribe to (None for all)
        """
        self.zmq_address = zmq_address
        self.symbols = symbols
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.running = False
        self.tick_data = {}  # Store latest tick data by symbol
        self.tick_history = {}  # Store historical tick data by symbol
        self.max_history = 1000  # Maximum number of ticks to store per symbol
        
    def connect(self) -> None:
        """Connect to the ZeroMQ server"""
        print(f"Connecting to MT5 tick server at {self.zmq_address}...")
        self.socket.connect(self.zmq_address)
        
        # Subscribe to topics
        if self.symbols is None:
            # Subscribe to all tick data
            self.socket.setsockopt_string(zmq.SUBSCRIBE, "TICK|")
            print("Subscribed to all symbols")
        else:
            # Subscribe to specific symbols
            for symbol in self.symbols:
                self.socket.setsockopt_string(zmq.SUBSCRIBE, f"TICK|{symbol}")
                print(f"Subscribed to symbol: {symbol}")
    
    def start(self) -> None:
        """Start receiving tick data"""
        self.running = True
        self.receive_thread = threading.Thread(target=self._receive_loop)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        
    def stop(self) -> None:
        """Stop receiving tick data"""
        self.running = False
        if hasattr(self, 'receive_thread'):
            self.receive_thread.join(timeout=1.0)
        self.socket.close()
        self.context.term()
        
    def _receive_loop(self) -> None:
        """Main loop to receive and process tick data"""
        while self.running:
            try:
                # Receive message with timeout
                if self.socket.poll(timeout=100) != 0:
                    message = self.socket.recv_string()
                    
                    # Process the message
                    parts = message.split('|', 2)
                    if len(parts) == 3:
                        msg_type, symbol, payload = parts
                        
                        if msg_type == "TICK":
                            self._process_tick(symbol, payload)
                    else:
                        print(f"Invalid message format: {message}")
            except zmq.ZMQError as e:
                print(f"ZMQ Error: {e}")
                time.sleep(0.1)
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(0.1)
    
    def _process_tick(self, symbol: str, payload: str) -> None:
        """Process a tick data message"""
        try:
            tick_data = json.loads(payload)
            
            # Convert Unix timestamp to datetime
            if "time" in tick_data:
                tick_time = datetime.fromtimestamp(tick_data["time"])
                tick_data["datetime"] = tick_time
            
            # Store the latest tick data
            self.tick_data[symbol] = tick_data
            
            # Store in history
            if symbol not in self.tick_history:
                self.tick_history[symbol] = []
            
            self.tick_history[symbol].append(tick_data)
            
            # Limit history size
            if len(self.tick_history[symbol]) > self.max_history:
                self.tick_history[symbol] = self.tick_history[symbol][-self.max_history:]
            
            # Print tick info
            print(f"Tick: {symbol} Bid: {tick_data.get('bid')} Ask: {tick_data.get('ask')} Time: {tick_data.get('datetime')}")
            
        except json.JSONDecodeError:
            print(f"Invalid JSON data: {payload}")
        except Exception as e:
            print(f"Error processing tick: {e}")
    
    def get_latest_tick(self, symbol: str) -> Optional[Dict]:
        """Get the latest tick data for a symbol"""
        return self.tick_data.get(symbol)
    
    def get_tick_history(self, symbol: str) -> List[Dict]:
        """Get the tick history for a symbol"""
        return self.tick_history.get(symbol, [])
    
    def get_tick_dataframe(self, symbol: str) -> pd.DataFrame:
        """Get the tick history as a pandas DataFrame"""
        history = self.get_tick_history(symbol)
        if not history:
            return pd.DataFrame()
        return pd.DataFrame(history)


def main():
    """Main function"""
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print("Stopping tick subscriber...")
        if 'subscriber' in locals():
            subscriber.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="MT5 Tick Data Subscriber")
    parser.add_argument("--address", type=str, default="tcp://localhost:5555",
                        help="ZeroMQ address (default: tcp://localhost:5555)")
    parser.add_argument("--symbols", type=str, nargs="*",
                        help="Symbols to subscribe to (default: all)")
    args = parser.parse_args()
    
    # Create and start the subscriber
    subscriber = MT5TickSubscriber(zmq_address=args.address, symbols=args.symbols)
    subscriber.connect()
    subscriber.start()
    
    print("MT5 Tick Subscriber started. Press Ctrl+C to exit.")
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        subscriber.stop()


if __name__ == "__main__":
    main() 