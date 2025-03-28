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
import sqlite3
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
        
        # For gap analysis
        self.previous_bids = {}  # Track previous bid for each symbol
        self.minute_start_time = None  # Current minute for aggregation
        self.gap_counts = {}  # {symbol: {'large': count, 'small': count}}
        
        # Database connection
        self.db_conn = None
        self.db_file = "tick_gap_data.db"
        
    def connect(self) -> None:
        """Connect to the ZeroMQ server and initialize database"""
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
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database"""
        try:
            self.db_conn = sqlite3.connect(self.db_file, check_same_thread=False)
            cursor = self.db_conn.cursor()
            
            # Create table for gap analysis
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS tick_gaps (
                timestamp INTEGER,
                symbol TEXT,
                minute TEXT,
                large_gap_count INTEGER,
                small_gap_count INTEGER,
                PRIMARY KEY (timestamp, symbol)
            )
            ''')
            
            self.db_conn.commit()
            print(f"Database initialized at {self.db_file}")
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            if self.db_conn:
                self.db_conn.close()
            self.db_conn = None
    
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
        
        # Save any remaining data and close database
        if self.minute_start_time and self.gap_counts:
            self._save_gap_counts()
        
        if self.db_conn:
            self.db_conn.close()
            print("Database connection closed")
        
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
    
    def _get_pip_size(self, symbol: str) -> float:
        """Determine pip size for the given symbol"""
        # Standard pip sizes for common forex pairs
        # Adjust as needed for your specific symbols
        if symbol.endswith("JPY"):
            return 0.01  # 2 decimal places
        else:
            return 0.0001  # 4 decimal places
    
    def _process_tick(self, symbol: str, payload: str) -> None:
        """Process a tick data message and analyze price gaps"""
        try:
            tick_data = json.loads(payload)
            
            # Get current bid price and time
            current_bid = tick_data.get("bid")
            if current_bid is None:
                return  # Skip if no bid price
            
            # Convert Unix timestamp to datetime
            if "time" in tick_data:
                tick_time = datetime.fromtimestamp(tick_data["time"])
                tick_data["datetime"] = tick_time
                
                # Get current minute
                current_minute = tick_time.replace(second=0, microsecond=0)
                
                # If this is a new minute, save previous minute data
                if self.minute_start_time is not None and current_minute != self.minute_start_time:
                    self._save_gap_counts()
                    # Reset counts for new minute
                    self.gap_counts = {}
                
                # Update current minute
                self.minute_start_time = current_minute
                
                # Ensure we have an entry for this symbol
                if symbol not in self.gap_counts:
                    self.gap_counts[symbol] = {"large": 0, "small": 0}
                
                # Calculate gap from previous bid if available
                if symbol in self.previous_bids:
                    prev_bid = self.previous_bids[symbol]
                    pip_size = self._get_pip_size(symbol)
                    
                    # Calculate gap in pips
                    gap_pips = abs(current_bid - prev_bid) / pip_size
                    
                    # Count as large or small gap
                    if gap_pips >= 1.0:
                        self.gap_counts[symbol]["large"] += 1
                        print(f"Large gap ({gap_pips:.2f} pips): {symbol} {prev_bid} -> {current_bid}")
                    else:
                        self.gap_counts[symbol]["small"] += 1
                        print(f"Small gap ({gap_pips:.2f} pips): {symbol} {prev_bid} -> {current_bid}")
            
            # Update the latest tick data and previous bid
            self.tick_data[symbol] = tick_data
            self.previous_bids[symbol] = current_bid
            
        except json.JSONDecodeError:
            print(f"Invalid JSON data: {payload}")
        except Exception as e:
            print(f"Error processing tick: {e}")
    
    def _save_gap_counts(self) -> None:
        """Save the current minute's gap counts to database"""
        if not self.db_conn or not self.minute_start_time:
            return
        
        timestamp = int(self.minute_start_time.timestamp())
        minute_str = self.minute_start_time.strftime("%Y-%m-%d %H:%M:00")
        
        try:
            cursor = self.db_conn.cursor()
            
            for symbol, counts in self.gap_counts.items():
                cursor.execute('''
                INSERT OR REPLACE INTO tick_gaps 
                (timestamp, symbol, minute, large_gap_count, small_gap_count) 
                VALUES (?, ?, ?, ?, ?)
                ''', (
                    timestamp, 
                    symbol, 
                    minute_str,
                    counts["large"], 
                    counts["small"]
                ))
            
            self.db_conn.commit()
            print(f"Saved gap counts for {len(self.gap_counts)} symbols at {minute_str}")
            
        except sqlite3.Error as e:
            print(f"Database error during save: {e}")
    
    def get_latest_tick(self, symbol: str) -> Optional[Dict]:
        """Get the latest tick data for a symbol"""
        return self.tick_data.get(symbol)


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
    print("Collecting tick gaps and saving to database every minute.")
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        subscriber.stop()


if __name__ == "__main__":
    main() 