#!/bin/bash

# Script to manage MetaTrader 5 Docker container

show_help() {
    echo "MetaTrader 5 Docker Management Script"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  setup     - Build and start the container"
    echo "  install   - Install MetaTrader 5 (run only once)"
    echo "  start     - Start the MetaTrader 5 application"
    echo "  stop      - Stop the container"
    echo "  restart   - Restart the container"
    echo "  logs      - Show container logs"
    echo "  shell     - Access shell inside the container"
    echo "  help      - Show this help message"
    echo ""
}

case "$1" in
    setup)
        echo "Building and starting MetaTrader 5 container..."
        docker-compose up -d
        echo "Container is running. VNC server available at localhost:5900"
        ;;
    install)
        echo "Starting MetaTrader 5 installation..."
        echo "Connect to VNC at localhost:5900 to complete the graphical installation"
        docker exec -it mt5 install
        ;;
    start)
        echo "Starting MetaTrader 5 application..."
        echo "Connect to VNC at localhost:5900 to see the application"
        docker exec -it mt5 start
        ;;
    stop)
        echo "Stopping container..."
        docker-compose down
        ;;
    restart)
        echo "Restarting container..."
        docker-compose restart
        ;;
    logs)
        docker-compose logs -f
        ;;
    shell)
        echo "Opening shell in container..."
        docker exec -it mt5 bash
        ;;
    help|*)
        show_help
        ;;
esac 