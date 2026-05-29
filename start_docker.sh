#!/bin/bash
set -euo pipefail

# Build CLI args from environment variables. Anything left unset falls through
# to the argparse defaults in horus_rotator.py.
ARGS=()
[[ -n "${HORUS_UDP_PORT:-}" ]]            && ARGS+=(--port "$HORUS_UDP_PORT")
[[ -n "${ROTATOR_IP:-}" ]]                && ARGS+=(--rotator_ip "$ROTATOR_IP")
[[ -n "${ROTATOR_PORT:-}" ]]              && ARGS+=(--rotator_port "$ROTATOR_PORT")
[[ -n "${ROTATOR_UPDATE_THRESHOLD:-}" ]]  && ARGS+=(--rotator_update_threshold "$ROTATOR_UPDATE_THRESHOLD")
[[ -n "${ROTATOR_UPDATE_RATE:-}" ]]       && ARGS+=(--rotator_update_rate "$ROTATOR_UPDATE_RATE")
[[ -n "${CALLSIGN_TIMEOUT:-}" ]]          && ARGS+=(--timeout "$CALLSIGN_TIMEOUT")
[[ -n "${STATION_LAT:-}" ]]               && ARGS+=(--lat "$STATION_LAT")
[[ -n "${STATION_LON:-}" ]]               && ARGS+=(--lon "$STATION_LON")
[[ -n "${STATION_ALT:-}" ]]               && ARGS+=(--alt "$STATION_ALT")
[[ -n "${GPS_DEVICE:-}" ]]                && ARGS+=(--gps "$GPS_DEVICE")
[[ -n "${GPS_BAUDRATE:-}" ]]              && ARGS+=(--baudrate "$GPS_BAUDRATE")

# Callsigns: space-separated list, intentionally unquoted for word splitting.
if [[ -n "${CALLSIGNS:-}" ]]; then
	ARGS+=(--callsigns)
	# shellcheck disable=SC2206
	ARGS+=($CALLSIGNS)
fi

case "${VERBOSE:-}" in
	1|true|TRUE|yes|YES) ARGS+=(--verbose) ;;
esac

exec python3 horus_rotator/horus_rotator.py "${ARGS[@]}"