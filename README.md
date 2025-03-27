# MetaTrader 5 with ZeroMQ in Docker

This project provides a Docker setup for running MetaTrader 5 with ZeroMQ support, allowing you to stream real-time tick data from MT5 to external applications.

## Features

- MetaTrader 5 running in a Docker container
- ZeroMQ integration for streaming real-time tick data
- Python client for receiving and processing tick data
- VNC access to the MT5 interface

## Prerequisites

- Docker and docker-compose installed
- Basic knowledge of MetaTrader 5 and ZeroMQ

## Getting Started

### 1. Clone this repository

```bash
git clone https://github.com/yourusername/mt5-docker.git
cd mt5-docker
```

### 2. Build and start the Docker container

```bash
docker-compose up -d
```

This starts the MT5 container with VNC access on port 5900.

### 3. Install MetaTrader 5

If MetaTrader 5 is not already installed in your volume:

```bash
docker exec -it mt5 /entrypoint.sh install
```

Follow the installation prompts through the VNC connection.

### 4. Set up ZeroMQ for MetaTrader 5

```bash
docker exec -it mt5 /entrypoint.sh setup-zmq
```

This will copy the necessary ZeroMQ files to the MetaTrader 5 installation.

### 5. Connect to the VNC server

Connect to `localhost:5900` using a VNC client like VNC Viewer.

### 6. Add the ZmqTickStreamer EA to a chart in MetaTrader 5

1. In MetaTrader 5, open a chart for the symbol you want to stream
2. Go to Navigator > Expert Advisors
3. Find ZmqTickStreamer EA and drag it onto the chart
4. Configure parameters if needed
5. Click OK to start the EA

### 7. Run the Python client to receive tick data

```bash
docker exec -it mt5 python3 /python/receive_ticks.py
```

You should now see the tick data being streamed from MetaTrader 5 to the Python client.

## Custom Python Client

You can also run the Python client outside of the Docker container:

```bash
cd python
pip install -r requirements.txt
python receive_ticks.py --address tcp://localhost:5555 --symbols EURUSD GBPUSD
```

## Configuration Options

### ZmqTickStreamer EA Parameters

- `ZMQ_PUB_ADDRESS`: ZeroMQ publisher address (default: tcp://*:5555)
- `ENABLE_TICK_DATA`: Enable tick data streaming (default: true)
- `ENABLE_BAR_DATA`: Enable bar data streaming on new bar (default: false)
- `TICK_PUBLISH_RATE`: Tick publishing rate (1 = every tick, 10 = every 10th tick)

### Python Client Parameters

- `--address`: ZeroMQ server address (default: tcp://localhost:5555)
- `--symbols`: List of symbols to subscribe to (default: all symbols)

## Ports

- 5900: VNC server for MetaTrader 5 GUI access
- 5555: ZeroMQ port for data streaming

## How It Works

1. The ZmqTickStreamer EA runs in MetaTrader 5 and publishes tick data using ZeroMQ
2. External applications connect to the ZeroMQ port and subscribe to tick data
3. The Python client receives and processes the tick data in real-time

## Troubleshooting

### No connection to ZeroMQ server

- Make sure the ZmqTickStreamer EA is running in MetaTrader 5
- Check that port 5555 is exposed in docker-compose.yml
- Verify the ZeroMQ address in both the EA and Python client match

### EA doesn't appear in MetaTrader 5

- Verify that the setup-zmq script ran successfully
- Restart MetaTrader 5 after setting up ZeroMQ
- Check MT5 logs for any errors

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- ZeroMQ for the messaging library
- MetaQuotes for MetaTrader 5 