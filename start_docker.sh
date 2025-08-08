#!/bin/bash

python3 horus_rotator/horus_rotator.py --rotator_ip 127.0.0.1 --rotator_port 4533 \
	--lat 38.0932 --lon -97.9179 --gps /dev/ttyUSB0 \
	--callsigns K5RWK KE5GDB --port 55673 -v
