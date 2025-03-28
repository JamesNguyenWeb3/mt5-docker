#!/usr/bin/env python
"""
Tick Gap Statistics Viewer
==========================

This script queries the tick_gap_data.db database and displays statistics
about large and small bid price gaps.
"""

import sqlite3
import pandas as pd
import argparse
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

def connect_to_db(db_file="tick_gap_data.db"):
    """Connect to the SQLite database"""
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        return None

def get_gap_stats(conn, symbol=None, start_time=None, end_time=None):
    """Query gap statistics from the database"""
    try:
        cursor = conn.cursor()
        
        # Build the query based on filters
        query = "SELECT timestamp, symbol, minute, large_gap_count, small_gap_count FROM tick_gaps"
        params = []
        
        where_clauses = []
        if symbol:
            where_clauses.append("symbol = ?")
            params.append(symbol)
        
        if start_time:
            where_clauses.append("timestamp >= ?")
            params.append(int(start_time.timestamp()))
        
        if end_time:
            where_clauses.append("timestamp <= ?")
            params.append(int(end_time.timestamp()))
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        
        query += " ORDER BY timestamp, symbol"
        
        # Execute the query
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=["timestamp", "symbol", "minute", "large_gap_count", "small_gap_count"])
        
        # Convert timestamp to datetime
        if not df.empty:
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="s")
        
        return df
    
    except sqlite3.Error as e:
        print(f"Database query error: {e}")
        return pd.DataFrame()

def display_summary(df):
    """Display summary statistics"""
    if df.empty:
        print("No data found matching the criteria.")
        return
    
    # Overall summary
    total_large = df["large_gap_count"].sum()
    total_small = df["small_gap_count"].sum()
    total_minutes = len(df)
    
    print(f"\n===== SUMMARY STATISTICS =====")
    print(f"Total minutes analyzed: {total_minutes}")
    print(f"Total large gaps (≥1 pip): {total_large}")
    print(f"Total small gaps (<1 pip): {total_small}")
    print(f"Average large gaps per minute: {total_large / total_minutes:.2f}")
    print(f"Average small gaps per minute: {total_small / total_minutes:.2f}")
    
    # Summary by symbol
    if len(df["symbol"].unique()) > 1:
        print("\n===== STATISTICS BY SYMBOL =====")
        symbol_stats = df.groupby("symbol").agg({
            "large_gap_count": "sum",
            "small_gap_count": "sum",
            "timestamp": "count"
        }).rename(columns={"timestamp": "minutes"})
        
        symbol_stats["avg_large_per_min"] = symbol_stats["large_gap_count"] / symbol_stats["minutes"]
        symbol_stats["avg_small_per_min"] = symbol_stats["small_gap_count"] / symbol_stats["minutes"]
        
        print(symbol_stats)

def plot_gaps(df, symbol=None):
    """Create a plot of gap counts over time"""
    if df.empty:
        print("No data to plot.")
        return
    
    # Filter by symbol if provided
    if symbol and symbol in df["symbol"].unique():
        plot_df = df[df["symbol"] == symbol]
        title = f"Tick Gap Counts for {symbol}"
    else:
        # Aggregate all symbols by minute
        plot_df = df.groupby("datetime").agg({
            "large_gap_count": "sum",
            "small_gap_count": "sum"
        }).reset_index()
        title = "Tick Gap Counts for All Symbols"
    
    # Create the plot
    plt.figure(figsize=(12, 6))
    plt.plot(plot_df["datetime"], plot_df["large_gap_count"], label="Large Gaps (≥1 pip)", color="red")
    plt.plot(plot_df["datetime"], plot_df["small_gap_count"], label="Small Gaps (<1 pip)", color="blue")
    plt.title(title)
    plt.xlabel("Time")
    plt.ylabel("Count")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    
    # Save and show
    plt.savefig(f"tick_gaps_{symbol or 'all'}.png")
    plt.show()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="View tick gap statistics")
    parser.add_argument("--db", type=str, default="tick_gap_data.db",
                        help="Database file (default: tick_gap_data.db)")
    parser.add_argument("--symbol", type=str,
                        help="Filter by symbol")
    parser.add_argument("--start", type=str,
                        help="Start time (format: YYYY-MM-DD HH:MM)")
    parser.add_argument("--end", type=str,
                        help="End time (format: YYYY-MM-DD HH:MM)")
    parser.add_argument("--plot", action="store_true",
                        help="Generate a plot of gap counts")
    args = parser.parse_args()
    
    # Parse time arguments
    start_time = None
    end_time = None
    
    if args.start:
        try:
            start_time = datetime.strptime(args.start, "%Y-%m-%d %H:%M")
        except ValueError:
            print("Invalid start time format. Use YYYY-MM-DD HH:MM")
            return
    
    if args.end:
        try:
            end_time = datetime.strptime(args.end, "%Y-%m-%d %H:%M")
        except ValueError:
            print("Invalid end time format. Use YYYY-MM-DD HH:MM")
            return
    
    # Connect to database
    conn = connect_to_db(args.db)
    if not conn:
        return
    
    # Get data
    df = get_gap_stats(conn, args.symbol, start_time, end_time)
    
    # Display summary
    display_summary(df)
    
    # Generate plot if requested
    if args.plot:
        plot_gaps(df, args.symbol)
    
    # Close connection
    conn.close()

if __name__ == "__main__":
    main() 