# MetaTrader 5 Docker Setup

This repository contains a Docker setup for running MetaTrader 5 on Ubuntu using Wine. The setup includes a VNC server so you can connect to the graphical interface remotely.

## Prerequisites

- Docker and Docker Compose installed on your host machine
- A VNC client (like VNC Viewer, RealVNC, or TightVNC)

## Building and Running

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/mt5-docker.git
   cd mt5-docker
   ```

2. Build and start the container:
   ```bash
   docker-compose up -d
   ```

3. Install MetaTrader 5 (first time only):
   
   On Windows:
   ```
   mt5.bat install
   ```
   
   On Linux/Mac:
   ```bash
   docker exec -it mt5 /entrypoint.sh install
   ```
   
   Note: You will need to follow the graphical installer through VNC (see next step).

4. Connect to the VNC server:
   - Open your VNC client
   - Connect to `localhost:5900` (or your server IP if remote)
   - No password is required by default (consider adding one for production use)

5. After installation, MetaTrader 5 should start automatically when the container starts.
   If you need to start it manually:
   
   On Windows:
   ```
   mt5.bat start
   ```
   
   On Linux/Mac:
   ```bash
   docker exec -it mt5 /entrypoint.sh start
   ```

## Windows Users

For Windows users, we've provided a `mt5.bat` script to make management easier:

- `mt5.bat setup` - Build and start the container
- `mt5.bat install` - Start the installation process
- `mt5.bat start` - Start MetaTrader 5
- `mt5.bat stop` - Stop the container
- `mt5.bat logs` - View container logs
- `mt5.bat shell` - Access a shell in the container

## Persisting Data

All MetaTrader 5 data is stored in a Docker volume named `mt5_data`. This ensures your settings, indicators, and account information persist between container restarts.

## Troubleshooting

### Display Issues

If you encounter display issues, you may need to adjust the resolution in the Dockerfile. Edit the Xvfb command in the scripts:

```
Xvfb :1 -screen 0 1024x768x16 &
```

Change `1024x768x16` to a resolution that works better for your setup.

### Wine Problems

If Wine has issues running MetaTrader 5, you might need to try a different Wine version. Edit the Dockerfile to install a specific version:

```
apt-get install -y --install-recommends winehq-stable
```

You could try `winehq-staging` or `winehq-devel` instead.

## Security Considerations

- The VNC server is exposed without a password. For production use, configure VNC with a password or use SSH tunneling.
- Consider adding a user and proper permissions in the Docker setup.

## License

This project is provided as-is under the MIT License. 