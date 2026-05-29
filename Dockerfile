FROM debian:bookworm-slim

WORKDIR /root/

# Install base packages
RUN apt-get -y update && \
    apt-get -y upgrade && \
    apt-get -y install --no-install-recommends \
      python3-pip && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps first so source changes don't bust the pip cache layer
COPY requirements.txt /root/horus_rotator/
RUN pip install --break-system-packages -r /root/horus_rotator/requirements.txt

COPY . /root/horus_rotator
RUN chmod +x /root/horus_rotator/start_docker.sh

# Run
ENTRYPOINT ["/root/horus_rotator/start_docker.sh"]