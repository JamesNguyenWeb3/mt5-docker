#!/usr/bin/env python
"""
ZeroMQ Tick Data Stress Test
============================

This script simulates high-frequency tick data to stress test the
tick processor. It publishes simulated tick data at high frequency
to verify the system can handle hundreds of ticks per second.
"""

import zmq
import json
import time
import random
import argparse
import threading
from datetime import datetime
import signal
import sys

class TickPublisher:
    """Publishes simulated tick data at high frequency"""
    
    def __init__(self, pub_address="tcp://*:5556", symbols=None, rate=100):
        """
        Initialize the tick publisher
        
        Args:
            pub_address: ZeroMQ publisher address to bind to
            symbols: List of symbols to publish (default: ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"])
            rate: Number of ticks per second to publish (default: 100)
        """
        self.pub_address = pub_address
        self.symbols = symbols or ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
        self.rate = rate
        self.running = False
        
        # Symbol baseline prices
        self.base_prices = {
            "EURUSD": 1.10000,
            "GBPUSD": 1.25000,
            "USDJPY": 150.000,
            "AUDUSD": 0.65000,
            # Add more symbols as needed
        }
        
        # Initialize ZeroMQ context and socket
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUB)
        
        # Stats
        self.tick_count = 0
        self.start_time = None
    
    def bind(self):
        """Bind the socket to the publisher address"""
        try:
            self.socket.bind(self.pub_address)
            print(f"Publisher bound to {self.pub_address}")
            return True
        except zmq.ZMQError as e:
            print(f"Failed to bind to {self.pub_address}: {e}")
            return False
    
    def start(self):
        """Start publishing tick data"""
        if self.running:
            return
        
        if not self.bind():
            return
        
        self.running = True
        self.start_time = time.time()
        self.publish_thread = threading.Thread(target=self._publish_loop)
        self.publish_thread.daemon = True
        self.publish_thread.start()
        
        # Start stats reporting thread
        self.stats_thread = threading.Thread(target=self._stats_loop)
        self.stats_thread.daemon = True
        self.stats_thread.start()
    
    def stop(self):
        """Stop publishing tick data"""
        self.running = False
        if hasattr(self, 'publish_thread'):
            self.publish_thread.join(timeout=1.0)
        if hasattr(self, 'stats_thread'):
            self.stats_thread.join(timeout=1.0)
        
        self.socket.close()
        self.context.term()
        
        duration = time.time() - self.start_time if self.start_time else 0
        print(f"\nPublished {self.tick_count} ticks in {duration:.2f} seconds")
        print(f"Average rate: {self.tick_count / duration:.2f} ticks/second")
    
    def _publish_loop(self):
        """Main loop to publish tick data"""
        sleep_time = 1.0 / self.rate
        
        while self.running:
            start = time.time()
            
            # Generate and publish a tick
            symbol = random.choice(self.symbols)
            tick = self._generate_tick(symbol)
            
            # Format the message according to ZmqTickStreamer protocol: "TICK|SYMBOL|{json data}"
            message = f"TICK|{symbol}|{json.dumps(tick)}"
            
            try:
                self.socket.send_string(message)
                self.tick_count += 1
            except zmq.ZMQError as e:
                print(f"Error sending tick: {e}")
            
            # Sleep for the remainder of the tick interval
            elapsed = time.time() - start
            remaining = sleep_time - elapsed
            if remaining > 0:
                time.sleep(remaining)
    
    def _stats_loop(self):
        """Report statistics periodically"""
        last_count = 0
        last_time = time.time()
        
        while self.running:
            time.sleep(1.0)  # Report every second
            
            now = time.time()
            current_count = self.tick_count
            
            # Calculate current tick rate
            ticks_since_last = current_count - last_count
            time_since_last = now - last_time
            current_rate = ticks_since_last / time_since_last if time_since_last > 0 else 0
            
            # Calculate overall average
            total_time = now - self.start_time if self.start_time else 0
            avg_rate = current_count / total_time if total_time > 0 else 0
            
            # Print stats
            print(f"\rPublished: {current_count} ticks | Current rate: {current_rate:.2f} ticks/s | " +
                  f"Average rate: {avg_rate:.2f} ticks/s", end="")
            
            # Update for next iteration
            last_count = current_count
            last_time = now
    
    def _generate_tick(self, symbol):
        """Generate a simulated tick for the given symbol"""
        base_price = self.base_prices.get(symbol, 1.0)
        
        # Add random price movement
        # For stress testing with larger gaps occasionally
        if random.random() < 0.05:  # 5% chance of a large move
            change = random.uniform(-0.005, 0.005)  # Large move (up to 50 pips)
        else:
            change = random.uniform(-0.0005, 0.0005)  # Small move (up to 5 pips)
        
        # Calculate new prices
        bid = base_price + change
        ask = bid + random.uniform(0.0001, 0.0003)  # Random spread
        
        # Update base price for next tick
        self.base_prices[symbol] = bid
        
        # Create tick data
        tick = {
            "symbol": symbol,
            "time": int(time.time()),
            "bid": round(bid, 5),
            "ask": round(ask, 5),
            "last": round((bid + ask) / 2, 5),
            "volume": random.randint(1, 100),
            "flags": 0
        }
        
        return tick


def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ZeroMQ Tick Data Stress Test")
    parser.add_argument("--address", type=str, default="tcp://*:5556",
                        help="ZeroMQ publisher address to bind to (default: tcp://*:5556)")
    parser.add_argument("--rate", type=int, default=100,
                        help="Number of ticks per second to publish (default: 100)")
    parser.add_argument("--symbols", type=str, nargs="+", 
                        default=["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"],
                        help="Symbols to include in the stress test")
    args = parser.parse_args()
    
    # Set up signal handler for graceful shutdown
    publisher = TickPublisher(args.address, args.symbols, args.rate)
    
    def signal_handler(sig, frame):
        print("\nStopping publisher...")
        publisher.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start publishing
    print(f"Starting tick publisher at rate: {args.rate} ticks/second")
    print(f"Publishing ticks for symbols: {', '.join(args.symbols)}")
    print("Press Ctrl+C to stop")
    
    publisher.start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        publisher.stop()


if __name__ == "__main__":
    main() 