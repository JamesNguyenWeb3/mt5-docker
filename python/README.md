# MetaTrader 5 ZeroMQ Tick Data Processing

This directory contains Python scripts for processing real-time tick data from MetaTrader 5 via ZeroMQ. The system analyzes price gaps (bid changes) in real-time and stores the statistics in a SQLite database.

## Features

- Real-time connection to MetaTrader 5 via ZeroMQ
- Analysis of bid price gaps (classifying them as "large" ≥1 pip or "small" <1 pip)
- Aggregation of gap counts per minute, per symbol
- Storage of aggregated data in SQLite database
- Visualization tools for analyzing the recorded data
- Stress testing capabilities to verify high-frequency data handling

## Installation

1. Install the required Python packages:

```bash
pip install -r requirements.txt
```

## Usage

### Receiving and Processing Tick Data

To start receiving tick data from MetaTrader 5:

```bash
python receive_ticks.py --address tcp://localhost:5555 --symbols EURUSD GBPUSD
```

Options:
- `--address`: ZeroMQ server address (default: tcp://localhost:5555)
- `--symbols`: List of symbols to subscribe to (default: all symbols)

The script will:
1. Connect to the MetaTrader 5 ZeroMQ publisher
2. Process incoming tick data in real-time
3. Calculate bid price gaps between consecutive ticks
4. Count large (≥1 pip) and small (<1 pip) gaps per minute
5. Save these counts to `tick_gap_data.db` (SQLite database)

### Viewing Gap Statistics

To view the recorded gap statistics:

```bash
python view_tick_gap_stats.py --symbol EURUSD --start "2023-05-01 09:00" --end "2023-05-01 17:00" --plot
```

Options:
- `--db`: Database file path (default: tick_gap_data.db)
- `--symbol`: Filter by symbol (optional)
- `--start`: Start time in format "YYYY-MM-DD HH:MM" (optional)
- `--end`: End time in format "YYYY-MM-DD HH:MM" (optional)
- `--plot`: Generate a plot of gap counts over time

### Stress Testing

To test if the system can handle high-frequency tick data:

```bash
python stress_test.py --rate 500 --symbols EURUSD GBPUSD USDJPY
```

This will simulate publishing tick data at the specified rate (ticks per second).

Options:
- `--address`: ZeroMQ publisher address to bind to (default: tcp://*:5556)
- `--rate`: Number of ticks per second to publish (default: 100)
- `--symbols`: Symbols to include in the stress test (default: EURUSD, GBPUSD, USDJPY, AUDUSD)

To run a stress test:
1. Start the stress test publisher on one terminal
2. Connect your tick processor to the stress test publisher in another terminal:
   ```bash
   python receive_ticks.py --address tcp://localhost:5556
   ```
3. Monitor performance to verify the system can handle hundreds of ticks per second

## Database Schema

The `tick_gaps` table in the SQLite database has the following structure:

| Column           | Type    | Description                               |
|------------------|---------|-------------------------------------------|
| timestamp        | INTEGER | Unix timestamp (start of the minute)      |
| symbol           | TEXT    | Symbol name (e.g., "EURUSD")              |
| minute           | TEXT    | Human-readable minute (YYYY-MM-DD HH:MM)  |
| large_gap_count  | INTEGER | Count of ticks with gaps ≥1 pip           |
| small_gap_count  | INTEGER | Count of ticks with gaps <1 pip           |

## Performance Considerations

- The system is designed to handle hundreds of ticks per second
- Data is aggregated per minute to reduce database load
- Use the stress testing tool to verify performance under high load
- SQLite is used for simplicity but can be replaced with a more robust database like PostgreSQL for production use

## Extending the System

- To change the gap threshold, modify the `_process_tick` method in `receive_ticks.py`
- To support additional instruments with different pip sizes, update the `_get_pip_size` method
- To add additional analytics, extend the data collection in `_process_tick` and add new columns to the database schema

## Troubleshooting

- If the MT5 ZeroMQ publisher isn't running, the client will keep trying to connect
- If you're experiencing data loss at high tick rates, try reducing the processing workload in `_process_tick`
- Check the SQLite database file permissions if you encounter write errors 