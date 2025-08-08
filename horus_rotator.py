# Design goals
# - Add park position after long timeout
# - Sondehub Import support

import logging
import argparse
#from threading import Thread
#from datetime import datetime, timedelta
from dateutil.parser import parse
import time

from earthmaths import *
from listeners import UDPListener
from gps import SerialGPS
from rotator import Rotator

threads = []
rotator_object = None
callsigns = []
callsigns_last_heard = []


def check_callsign(callsign):
    """ Determine if payload summary packet should be considered for rotator control. This function
    evaluates the callsign against the priority list, and factors in the timeout value."""

    global callsigns_last_heard

    logging.info(callsigns)
    logging.info(callsigns_last_heard)

    # No callsign list, so point to the packet
    if len(callsigns) == 0:
        return True

    # Update last heard value if callsign is in the list
    if callsign in callsigns:
        callsigns_last_heard[callsigns.index(callsign)] = time.time()
    else:
        logging.debug(f"Callsign {callsign} not in callsigns")
        return False

    # If first in list (highest priority), return true
    if callsign == callsigns[0]:
        return True

    # Iterate through callsign list and check timeouts.
    _timeout = 0
    if len(callsigns) > 1:
        for call in callsigns:
            # Add time to timeout for later payloads
            _timeout += timeout

            if (callsigns_last_heard[callsigns.index(call)] - time.time()) < _timeout:
                logging.debug(f"Callsign {call} not timed out yet for incoming callsign {callsign}")
                return False
            else:
                return True


def udp_listener_summary_callback(data):
    """ Handle a Payload Summary Message from UDPListener """

    # Modem stats messages are also passed in via this callback.
    # handle them separately.
    if data["type"] == "MODEM_STATS":
        return

    # Otherwise, we have a PAYLOAD_SUMMARY message.

    # Extract the fields we need.
    # Convert to something generic we can pass onwards.
    output = {}
    output["lat"] = float(data["latitude"])
    output["lon"] = float(data["longitude"])
    output["alt"] = float(data["altitude"])
    output["callsign"] = data["callsign"]

    if "time" in data.keys():
        _time = data["time"]
    else:
        _time = "??:??:??"

    use_packet = check_callsign(output["callsign"])

    logging.info(
        "Horus UDP Data (%s): %s, %s, %.5f, %.5f, %.1f"
        % ("usable" if use_packet else "discarded", output["callsign"], _time, output["lat"], output["lon"], output["alt"])
    )

    try:
        if rotator_object and use_packet:
            rotator_object.add(output)
    except Exception as e:
        logging.error("Error Handling Payload Position - %s" % str(e))


def udp_listener_car_callback(data):
    """ Handle car position data """
    _lat = float(data["latitude"])
    _lon = float(data["longitude"])

    # Handle when GPSD and/or other GPS data sources return a n/a for altitude.
    try:
        _alt = float(data["altitude"])
    except:
        _alt = 0.0

    logging.debug("Local Position: %.5f, %.5f, %.1f" % (_lat, _lon, _alt))

    if rotator_object:
        rotator_object.update_station_position(_lat, _lon, _alt)

if __name__ == "__main__":
    # Define operating parameters
    parser = argparse.ArgumentParser(description="Horus UDP payload summaries to rotator control")

    parser.add_argument("--port", required=False, default=55672, type=int,
                        help="Horus UDP port (default 55672)")
    parser.add_argument("--rotator_ip", required=False, default="localhost", type=str,
                        help="IP address of rotctld instance (default localhost)")
    parser.add_argument("--rotator_port", required=False, default=4533, type=int,
                        help="Port of rotctld instance (default 4533)")
    parser.add_argument("--rotator_update_threshold", required=False, default=5, type=int,
                        help="Update threshold of rotator in degrees (default 5)")
    parser.add_argument("--rotator_update_rate", required=False, default=10, type=int,
                        help="Update rate of rotator in seconds (default 10)")
    parser.add_argument("--callsigns", nargs="*", required=False, default=[],
                        help="Payload callsign(s) or ID(s) (separated by space) to consider for rotator control. If none are listed, then the rotator will respond to any payload summaries received")
    parser.add_argument("--timeout", required=False, default=60, 
                        help="Timeout time (in seconds) before evaluating other callsigns for rotator control (default 60)")
    parser.add_argument("--lat", required=False, default=0.0, 
                        help="Receiver location latitude (north positive)")
    parser.add_argument("--lon", required=False, default=0.0, 
                        help="Receiver location longitude (east positive)")
    parser.add_argument("--alt", required=False, default=0.0, 
                        help="Receiver location altitude (meters above sea level)")
    parser.add_argument("--gps", required=False, default=None, type=str,
                        help="GPS receiver serial port (if equipped)")
    parser.add_argument("--baudrate", required=False, default=38400,
                        help="GPS receiver baudrate (not needed for u-blox USB GPS units)")
    parser.add_argument("-v", "--verbose", action='store_true',
                        help="Verbose")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    horus_port = args.port

    rotator_ip = args.rotator_ip
    rotator_port = args.rotator_port
    rotator_update_threshold = int(args.rotator_update_threshold)

    callsigns = args.callsigns
    timeout = int(args.timeout)

    logging.info(f"Using callsigns {callsigns} and timeout {timeout}")

    callsigns_last_heard = []

    for callsign in callsigns:
        callsigns_last_heard.append(time.time() - timeout)


    rx_lat = float(args.lat)
    rx_lon = float(args.lon)
    rx_alt = float(args.alt)

    gps = args.gps
    gps_baudrate = args.baudrate

    threads = []

    # Telemetry via Horus UDP - Start up a listener
    logging.info(
        "Starting Telemetry Horus UDP listener on port %d"
        % horus_port
    )
    _telem_horus_udp_listener = UDPListener(
        summary_callback=udp_listener_summary_callback,
        gps_callback=None,
        bearing_callback=None,
        port=horus_port,
    )
    _telem_horus_udp_listener.start()
    threads.append(_telem_horus_udp_listener)

    if gps:
        # Serial GPS Source.
        logging.info("Starting Serial GPS Listener.")
        _serial_gps = SerialGPS(
            serial_port=gps,
            serial_baud=gps_baudrate,
            callback=udp_listener_car_callback,
        )
        threads.append(_serial_gps)

    _rotator = Rotator(
        station_position=(
            rx_lat,
            rx_lon,
            rx_alt,
        ),
        rotctld_host=rotator_ip,
        rotctld_port=rotator_port,
        rotator_update_rate=3,
        rotator_update_threshold=5,
        rotator_homing_enabled=False,
        rotator_homing_delay=600,
        rotator_home_position=[
            0,
            90,
        ],
        azimuth_only=False
    )

    threads.append(_rotator)

    rotator_object = _rotator

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Keyboard interrupt!")

    for _thread in threads:
        try:
            _thread.close()
        except Exception as e:
            logging.error("Error closing thread - %s" % str(e))
