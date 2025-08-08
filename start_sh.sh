#!/bin/bash

venv/bin/python3 horus_rotator.py --rotator_ip 127.0.0.1 --rotator_port 4533 \
	--lat 38.0932 --lon -97.9179 --gps /dev/serial/by-id/usb-u-blox_AG_-_www.u-blox.com_u-blox_7_-_GPS_GNSS_Receiver-if00 \
	--callsigns K5RWK K5UTD --port 55673 --verbose
