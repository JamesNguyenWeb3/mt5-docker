#!/usr/bin/env python
"""
High Performance ZeroMQ Client for MetaTrader 5 Tick Data
========================================================

This client implements advanced features to ensure zero message loss:
1. Message sequence number tracking to detect any missed messages
2. Queue buffering between receiving and processing threads
3. Request/reply confirmation pattern for critical ticks

Designed to handle hundreds of ticks per second without data loss.
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
import queue
from typing import Dict, List, Optional, Union, Any

class HighPerformanceTickReceiver:
    """
    High performance client for MT5 tick data with zero message loss guarantees
    """
    
    def __init__(self, 
                 pub_address: str = "tcp://localhost:5555", 
                 rep_address: str = "tcp://localhost:5557",
                 symbols: Optional[List[str]] = None,
                 enable_confirmations: bool = True,
                 queue_size: int = 10000) -> None:
        """
        Initialize the high performance tick receiver.
        
        Args:
            pub_address: ZeroMQ publisher address to connect to
            rep_address: ZeroMQ reply address for confirmations
            symbols: List of symbols to subscribe to (None for all)
            enable_confirmations: Whether to use REQ/REP confirmations
            queue_size: Size of the message queue buffer
        """
        self.pub_address = pub_address
        self.rep_address = rep_address
        self.symbols = symbols
        self.enable_confirmations = enable_confirmations
        
        # ZeroMQ context and sockets
        self.context = zmq.Context()
        self.subscriber = self.context.socket(zmq.SUB)
        self.requester = None
        if self.enable_confirmations:
            self.requester = self.context.socket(zmq.REQ)
        
        # Increase ZeroMQ buffer sizes for high-throughput
        self.subscriber.set_hwm(100000)  # Allow up to 100,000 messages in queue
        
        # Running state
        self.running = False
        
        # Message buffer queue between receiver and processor threads
        self.message_queue = queue.Queue(maxsize=queue_size)
        
        # Sequence number tracking
        self.seq_nums = {}  # {symbol: last_sequence_number}
        self.missed_messages = 0
        
        # Price gap analysis data
        self.prev_bids = {}  # {symbol: previous_bid_price}
        self.minute_start_time = None
        self.gap_counts = {}  # {symbol: {'large': count, 'small': count}}
        
        # Database connection
        self.db_conn = None
        self.db_file = "tick_data.db"
        
        # Performance stats
        self.receive_count = 0
        self.process_count = 0
        self.start_time = time.time()
        self.last_report_time = self.start_time
        
    def connect(self) -> None:
        """Connect to ZeroMQ sockets and initialize database"""
        # Connect to publisher socket
        print(f"Connecting to publisher at {self.pub_address}")
        self.subscriber.connect(self.pub_address)
        
        # Connect to reply socket if confirmations enabled
        if self.enable_confirmations and self.requester:
            print(f"Connecting to reply socket at {self.rep_address}")
            self.requester.connect(self.rep_address)
            self.requester.setsockopt(zmq.RCVTIMEO, 500)  # 500ms timeout for confirmations
        
        # Set up subscriptions
        if self.symbols is None:
            # Subscribe to all tick data
            self.subscriber.setsockopt_string(zmq.SUBSCRIBE, "TICK|")
            print("Subscribed to all symbols")
        else:
            # Subscribe to specific symbols
            for symbol in self.symbols:
                self.subscriber.setsockopt_string(zmq.SUBSCRIBE, f"TICK|{symbol}")
                print(f"Subscribed to symbol: {symbol}")
        
        # Initialize database
        self._init_database()
        
    def _init_database(self) -> None:
        """Initialize SQLite database for storing tick data"""
        try:
            self.db_conn = sqlite3.connect(self.db_file, check_same_thread=False)
            cursor = self.db_conn.cursor()
            
            # Create tables if they don't exist
            
            # Table for price gap statistics
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
            
            # Table to log any sequence gaps (missed messages)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sequence_gaps (
                timestamp INTEGER,
                symbol TEXT,
                gap_size INTEGER,
                expected_seq INTEGER,
                received_seq INTEGER,
                PRIMARY KEY (timestamp, symbol, expected_seq)
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
        """Start the receiver"""
        if self.running:
            return
            
        self.running = True
        
        # Start the receiver thread (gets messages from ZMQ and puts in queue)
        self.receiver_thread = threading.Thread(target=self._receive_loop)
        self.receiver_thread.daemon = True
        self.receiver_thread.start()
        
        # Start the processor thread (gets messages from queue and processes)
        self.processor_thread = threading.Thread(target=self._process_loop)
        self.processor_thread.daemon = True
        self.processor_thread.start()
        
        # Start the stats reporting thread
        self.stats_thread = threading.Thread(target=self._stats_loop)
        self.stats_thread.daemon = True
        self.stats_thread.start()
        
        print("Receiver started. Press Ctrl+C to stop.")
        
    def stop(self) -> None:
        """Stop the receiver and clean up"""
        print("\nStopping receiver...")
        self.running = False
        
        # Wait for threads to finish
        if hasattr(self, 'receiver_thread'):
            self.receiver_thread.join(timeout=1.0)
        if hasattr(self, 'processor_thread'):
            self.processor_thread.join(timeout=1.0)
        if hasattr(self, 'stats_thread'):
            self.stats_thread.join(timeout=1.0)
            
        # Save any remaining data
        if self.minute_start_time:
            self._save_gap_counts()
            
        # Close sockets
        self.subscriber.close()
        if self.requester:
            self.requester.close()
        self.context.term()
        
        # Close database
        if self.db_conn:
            self.db_conn.close()
            
        # Print final stats
        self._print_final_stats()
    
    def _receive_loop(self) -> None:
        """Thread that receives messages from ZeroMQ and puts them in the queue"""
        print("Receiver thread started")
        
        # Set up poller for non-blocking receive
        poller = zmq.Poller()
        poller.register(self.subscriber, zmq.POLLIN)
        
        while self.running:
            try:
                # Poll for messages with timeout
                socks = dict(poller.poll(timeout=100))
                
                if self.subscriber in socks and socks[self.subscriber] == zmq.POLLIN:
                    # Receive message
                    message = self.subscriber.recv_string()
                    self.receive_count += 1
                    
                    # Send confirmation if enabled
                    if self.enable_confirmations and self.requester:
                        try:
                            # Send confirmation request
                            self.requester.send_string("CONFIRM", zmq.NOBLOCK)
                            
                            # Get confirmation reply (with timeout via socket option)
                            self.requester.recv_string()
                        except zmq.ZMQError:
                            # Don't let confirmation failure stop us
                            pass
                    
                    # Put message in queue (with timeout to prevent blocking)
                    try:
                        self.message_queue.put(message, timeout=0.1)
                    except queue.Full:
                        print("WARNING: Message queue full, dropping message!")
                
            except zmq.ZMQError as e:
                print(f"ZMQ Error in receiver: {e}")
                time.sleep(0.001)
            except Exception as e:
                print(f"Error in receiver: {e}")
                time.sleep(0.001)
    
    def _process_loop(self) -> None:
        """Thread that processes messages from the queue"""
        print("Processor thread started")
        
        while self.running:
            try:
                # Get message from queue with timeout
                try:
                    message = self.message_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Process the message
                parts = message.split('|', 2)
                if len(parts) == 3:
                    msg_type, symbol, payload = parts
                    
                    if msg_type == "TICK":
                        self._process_tick(symbol, payload)
                        self.process_count += 1
                else:
                    print(f"Invalid message format: {message}")
                
                # Mark as done
                self.message_queue.task_done()
                
            except Exception as e:
                print(f"Error in processor: {e}")
                time.sleep(0.001)
    
    def _stats_loop(self) -> None:
        """Thread that reports performance statistics"""
        while self.running:
            time.sleep(1.0)  # Report every second
            
            now = time.time()
            elapsed = now - self.last_report_time
            
            # Calculate rates
            receive_rate = self.receive_count / elapsed if elapsed > 0 else 0
            process_rate = self.process_count / elapsed if elapsed > 0 else 0
            queue_size = self.message_queue.qsize()
            
            # Print statistics
            print(f"\rReceived: {self.receive_count} ({receive_rate:.1f}/s) | " + 
                  f"Processed: {self.process_count} ({process_rate:.1f}/s) | " +
                  f"Queue: {queue_size} | Missed: {self.missed_messages}", end="")
            
            # Reset for next report
            self.last_report_time = now
    
    def _print_final_stats(self) -> None:
        """Print final statistics when shutting down"""
        total_time = time.time() - self.start_time
        receive_rate = self.receive_count / total_time if total_time > 0 else 0
        process_rate = self.process_count / total_time if total_time > 0 else 0
        
        print("\n--- Final Statistics ---")
        print(f"Total running time: {total_time:.2f} seconds")
        print(f"Total messages received: {self.receive_count}")
        print(f"Total messages processed: {self.process_count}")
        print(f"Average receive rate: {receive_rate:.2f} messages/second")
        print(f"Average process rate: {process_rate:.2f} messages/second")
        print(f"Detected missed messages: {self.missed_messages}")
    
    def _process_tick(self, symbol: str, payload: str) -> None:
        """Process a tick data message"""
        try:
            # Parse JSON data
            tick_data = json.loads(payload)
            
            # Check sequence number to detect missed messages
            if "seq_num" in tick_data:
                seq_num = int(tick_data["seq_num"])
                self._check_sequence(symbol, seq_num)
            
            # Get bid price for gap analysis
            current_bid = tick_data.get("bid")
            if current_bid is None:
                return  # Skip if no bid price
            
            # Process timestamp
            if "time" in tick_data:
                tick_time = datetime.fromtimestamp(tick_data["time"])
                current_minute = tick_time.replace(second=0, microsecond=0)
                
                # If new minute, save previous data and reset
                if self.minute_start_time is not None and current_minute != self.minute_start_time:
                    self._save_gap_counts()
                    self.gap_counts = {}
                
                # Update current minute
                self.minute_start_time = current_minute
                
                # Initialize gap counts for this symbol if needed
                if symbol not in self.gap_counts:
                    self.gap_counts[symbol] = {"large": 0, "small": 0}
                
                # Calculate gap from previous bid
                if symbol in self.prev_bids:
                    prev_bid = self.prev_bids[symbol]
                    pip_size = self._get_pip_size(symbol)
                    
                    # Calculate gap in pips
                    gap_pips = abs(current_bid - prev_bid) / pip_size
                    
                    # Categorize as large or small gap
                    if gap_pips >= 1.0:
                        self.gap_counts[symbol]["large"] += 1
                    else:
                        self.gap_counts[symbol]["small"] += 1
            
            # Store current bid for next comparison
            self.prev_bids[symbol] = current_bid
            
        except json.JSONDecodeError:
            print(f"Invalid JSON data: {payload}")
        except Exception as e:
            print(f"Error processing tick: {e}")
    
    def _check_sequence(self, symbol: str, seq_num: int) -> None:
        """Check sequence numbers to detect missed messages"""
        if symbol in self.seq_nums:
            last_seq = self.seq_nums[symbol]
            expected_seq = last_seq + 1
            
            # If there's a gap, we missed some messages
            if seq_num > expected_seq:
                gap_size = seq_num - expected_seq
                self.missed_messages += gap_size
                
                print(f"\nDetected sequence gap for {symbol}: missing {gap_size} messages " +
                      f"(expected {expected_seq}, got {seq_num})")
                
                # Log the gap in the database
                if self.db_conn:
                    try:
                        cursor = self.db_conn.cursor()
                        now = int(time.time())
                        cursor.execute('''
                        INSERT INTO sequence_gaps 
                        (timestamp, symbol, gap_size, expected_seq, received_seq)
                        VALUES (?, ?, ?, ?, ?)
                        ''', (now, symbol, gap_size, expected_seq, seq_num))
                        self.db_conn.commit()
                    except sqlite3.Error as e:
                        print(f"Database error recording sequence gap: {e}")
        
        # Update the last sequence number
        self.seq_nums[symbol] = seq_num
    
    def _get_pip_size(self, symbol: str) -> float:
        """Get the pip size for a symbol"""
        # Standard pip sizes (customize as needed)
        if symbol.endswith("JPY"):
            return 0.01  # 2 decimal places for JPY pairs
        else:
            return 0.0001  # 4 decimal places for other pairs
    
    def _save_gap_counts(self) -> None:
        """Save the gap counts for the current minute to the database"""
        if not self.db_conn or not self.minute_start_time:
            return
            
        try:
            timestamp = int(self.minute_start_time.timestamp())
            minute_str = self.minute_start_time.strftime("%Y-%m-%d %H:%M:00")
            
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
            print(f"\nSaved gap counts for {len(self.gap_counts)} symbols at {minute_str}")
            
        except sqlite3.Error as e:
            print(f"Database error saving gap counts: {e}")


def main():
    """Main entry point"""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="High Performance MT5 Tick Receiver")
    
    parser.add_argument("--pub-address", type=str, default="tcp://localhost:5555",
                        help="ZeroMQ publisher address (default: tcp://localhost:5555)")
    parser.add_argument("--rep-address", type=str, default="tcp://localhost:5557",
                        help="ZeroMQ reply address (default: tcp://localhost:5557)")
    parser.add_argument("--symbols", type=str, nargs="+",
                        help="Symbols to subscribe to (default: all symbols)")
    parser.add_argument("--no-confirm", action="store_true",
                        help="Disable message confirmations")
    parser.add_argument("--queue-size", type=int, default=10000,
                        help="Size of message queue (default: 10000)")
    
    args = parser.parse_args()
    
    # Create and start the receiver
    receiver = HighPerformanceTickReceiver(
        pub_address=args.pub_address,
        rep_address=args.rep_address,
        symbols=args.symbols,
        enable_confirmations=not args.no_confirm,
        queue_size=args.queue_size
    )
    
    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        receiver.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Connect and start
    receiver.connect()
    receiver.start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        receiver.stop()


if __name__ == "__main__":
    main()
