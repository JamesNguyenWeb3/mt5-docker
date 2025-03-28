#!/usr/bin/env python
"""
Stress Test for High Performance Tick Receiver
==============================================

This script simulates high volume tick data to test the high performance
receiver's ability to handle bursts of market data without message loss.

It publishes simulated tick data at a configurable rate to stress test
the system's throughput and reliability mechanisms.

Usage:
    python stress_test_high_volume.py --rate 1000
"""

import sys
import json
import time
import argparse
import random
import threading
import zmq
from datetime import datetime

class TickPublisher:
    """Publishes simulated high-volume tick data"""

    def __init__(self, pub_address="tcp://*:5555", rep_address="tcp://*:5557"):
        """Initialize tick publisher"""
        self.pub_address = pub_address
        self.rep_address = rep_address
        
        # Symbols to generate ticks for
        self.symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD"]
        
        # ZeroMQ context and sockets
        self.context = zmq.Context()
        self.publisher = self.context.socket(zmq.PUB)
        self.replier = self.context.socket(zmq.REP)
        
        # Sequence numbers for each symbol
        self.seq_nums = {symbol: 0 for symbol in self.symbols}
        
        # Performance stats
        self.sent_count = 0
        self.confirm_count = 0
        self.start_time = None
        self.running = False
        
    def bind(self):
        """Bind to ZeroMQ sockets"""
        print(f"Binding publisher to {self.pub_address}")
        self.publisher.bind(self.pub_address)
        
        print(f"Binding reply socket to {self.rep_address}")
        self.replier.bind(self.rep_address)
        
    def start(self, rate=100):
        """Start publishing ticks at the specified rate (ticks per second)"""
        if self.running:
            return
            
        self.running = True
        self.start_time = time.time()
        
        # Start confirmation thread
        self.confirm_thread = threading.Thread(target=self._confirm_loop)
        self.confirm_thread.daemon = True
        self.confirm_thread.start()
        
        # Generate ticks
        print(f"Publishing simulated ticks at rate: {rate}/second")
        print("Press Ctrl+C to stop")
        
        try:
            delay = 1.0 / rate if rate > 0 else 0
            
            while self.running:
                # Generate and send a tick
                self._send_tick()
                
                # Sleep for calculated delay
                if delay > 0:
                    time.sleep(delay)
                
                # Print stats every second
                elapsed = time.time() - self.start_time
                if elapsed >= 1.0:
                    actual_rate = self.sent_count / elapsed
                    confirm_rate = self.confirm_count / elapsed
                    
                    print(f"\rRate: {actual_rate:.1f}/s | Sent: {self.sent_count} | " +
                          f"Confirmed: {self.confirm_count} | " +
                          f"Ratio: {(confirm_rate/actual_rate)*100:.1f}%", end="")
                    
                    self.sent_count = 0
                    self.confirm_count = 0
                    self.start_time = time.time()
                
        except KeyboardInterrupt:
            print("\nStopping publisher...")
        finally:
            self.stop()
    
    def _confirm_loop(self):
        """Thread to handle confirmation requests"""
        while self.running:
            try:
                # Use poll with timeout to avoid blocking
                if self.replier.poll(timeout=100) == zmq.POLLIN:
                    # Receive request
                    message = self.replier.recv_string()
                    
                    # Send reply
                    self.replier.send_string("CONFIRMED")
                    self.confirm_count += 1
            except zmq.ZMQError as e:
                print(f"ZMQ Error in confirmer: {e}")
                time.sleep(0.001)
            except Exception as e:
                print(f"Error in confirmer: {e}")
                time.sleep(0.001)
                
    def _send_tick(self):
        """Generate and send a simulated tick"""
        # Choose a random symbol
        symbol = random.choice(self.symbols)
        
        # Get and increment sequence number
        seq_num = self.seq_nums[symbol]
        self.seq_nums[symbol] += 1
        
        # Generate random price data
        if symbol == "USDJPY":
            # JPY pairs have different decimal places
            base_price = 150.00
            spread = 0.02
            bid = base_price + random.uniform(-0.5, 0.5)
            ask = bid + spread
        else:
            base_price = 1.1000
            spread = 0.0002
            bid = base_price + random.uniform(-0.02, 0.02)
            ask = bid + spread
        
        # Create tick data
        tick_data = {
            "symbol": symbol,
            "time": time.time(),
            "bid": bid,
            "ask": ask,
            "volume": random.randint(1, 10),
            "seq_num": seq_num
        }
        
        # Convert to JSON
        json_data = json.dumps(tick_data)
        
        # Send the message
        message = f"TICK|{symbol}|{json_data}"
        self.publisher.send_string(message)
        self.sent_count += 1
        
    def stop(self):
        """Stop the publisher and clean up"""
        self.running = False
        
        # Wait for confirmation thread to stop
        if hasattr(self, 'confirm_thread'):
            self.confirm_thread.join(timeout=1.0)
        
        # Close sockets
        self.publisher.close()
        self.replier.close()
        self.context.term()
        
        print("\nPublisher stopped")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Stress Test for MT5 High Performance Receiver")
    
    parser.add_argument("--rate", type=int, default=100,
                        help="Rate of ticks to send per second (default: 100)")
    parser.add_argument("--pub-address", type=str, default="tcp://*:5555",
                        help="ZeroMQ publisher address (default: tcp://*:5555)")
    parser.add_argument("--rep-address", type=str, default="tcp://*:5557",
                        help="ZeroMQ reply address (default: tcp://*:5557)")
    
    args = parser.parse_args()
    
    # Create and start publisher
    publisher = TickPublisher(
        pub_address=args.pub_address,
        rep_address=args.rep_address
    )
    
    # Bind and start
    publisher.bind()
    publisher.start(rate=args.rate)


if __name__ == "__main__":
    main()
