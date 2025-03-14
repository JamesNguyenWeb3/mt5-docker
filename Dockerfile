FROM ubuntu:22.04

# Set environment variables to non-interactive (avoid user prompts during installation)
ENV DEBIAN_FRONTEND=noninteractive

# Install necessary packages
RUN apt-get update && apt-get install -y \
    wget \
    gnupg2 \
    software-properties-common \
    xvfb \
    x11vnc \
    xterm \
    fluxbox \
    locales \
    && rm -rf /var/lib/apt/lists/*

# Set up locale
RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

# Install Wine
RUN dpkg --add-architecture i386 && \
    mkdir -pm755 /etc/apt/keyrings && \
    wget -O /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key && \
    wget -NP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/ubuntu/dists/jammy/winehq-jammy.sources && \
    apt-get update && \
    apt-get install -y --install-recommends winehq-stable && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd -m -s /bin/bash trader
USER trader
WORKDIR /home/trader

# Script to download and install MetaTrader 5
RUN echo '#!/bin/bash\n\
wget https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5ubuntu.sh && \
chmod +x mt5ubuntu.sh && \
Xvfb :1 -screen 0 1024x768x16 & \
export DISPLAY=:1 && \
./mt5ubuntu.sh' > /home/trader/install_mt5.sh && \
chmod +x /home/trader/install_mt5.sh

# Script to start MT5
RUN echo '#!/bin/bash\n\
Xvfb :1 -screen 0 1024x768x16 & \
export DISPLAY=:1 && \
wine ~/.wine/drive_c/Program\ Files/MetaTrader\ 5/terminal64.exe' > /home/trader/start_mt5.sh && \
chmod +x /home/trader/start_mt5.sh

# Script to setup VNC for remote access
RUN echo '#!/bin/bash\n\
Xvfb :1 -screen 0 1024x768x16 & \
export DISPLAY=:1 && \
x11vnc -display :1 -forever -shared & \
fluxbox &' > /home/trader/start_vnc.sh && \
chmod +x /home/trader/start_vnc.sh

# Switch back to root for entrypoint configuration
USER root

# Create entrypoint script with explicit commands
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["vnc"]

# Expose VNC port
EXPOSE 5900 