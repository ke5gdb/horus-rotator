FROM debian:bookworm-slim

WORKDIR /root/

# Install base packages
RUN apt-get -y update && \
    apt-get -y upgrade && \
    apt-get -y install --no-install-recommends \
      python3-venv \
      python3-pip 

COPY . /root/horus_rotator
RUN chmod +x /root/horus_rotator/start_docker.sh

RUN cd /root/horus_rotator && \
    pip install --break-system-packages -r requirements.txt

# Run 
ENTRYPOINT ["/root/horus_rotator/start_docker.sh"]
