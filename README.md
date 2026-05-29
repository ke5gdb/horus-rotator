# horus-rotator

Point an antenna rotator at a high-altitude balloon payload using Horus UDP telemetry.

`horus-rotator` listens for Project Horus *payload summary* UDP packets (the same packets emitted by [horus-gui](https://github.com/projecthorus/horus-gui) and other Horus demodulators), works out the azimuth and elevation from your station to the payload, and drives a [Hamlib rotctld](https://hamlib.github.io/) instance to track it. It supports a priority list of callsigns, a configurable timeout for falling back to lower-priority payloads, and an optional serial GPS for chase / mobile use.

---

## How it works

```
+--------------------+        UDP         +-----------------+      TCP       +-----------+
|  horus-gui  /      | ----- 55672 -----> |  horus-rotator  | -- rotctld --> | rotctld   |
|  horus_demod  /    |  payload_summary   |                 |   (4533)       | (Hamlib)  |
|  other Horus tx    |                    |                 |                |           |
+--------------------+                    +-----------------+                +-----------+
                                                  ^
                                       optional   |
                                       +----------+---------+
                                       |  Serial GPS (NMEA) |  (for chase / mobile rigs)
                                       +--------------------+
```

The application keeps your station position fixed (from `--lat/--lon/--alt`) unless you supply a GPS device, in which case it updates dynamically.

---

## Prerequisites

- A running **rotctld** instance configured for your rotator (`rotctld -m <model> -r <device> -t 4533`).
- A Horus UDP source on the network — typically `horus-gui` or `horusdemodlib`'s `horus_demod` — emitting payload summary packets on UDP/55672 (or whatever port you configure).
- (Optional) A u-blox or NMEA-compatible serial GPS for mobile installations.
- Either:
  - **Docker** with the Compose plugin, **or**
  - **Python 3.9+** with `pip` and `venv`.

---

## Quick start: Docker Compose (recommended)

1. Clone the repo:
   ```bash
   git clone https://github.com/<you>/horus-rotator.git
   cd horus-rotator
   ```

2. Edit [docker-compose.yml](docker-compose.yml) — at minimum, change:
   - `STATION_LAT` / `STATION_LON` to your station coordinates,
   - `CALLSIGNS` to the payload callsign(s) you want to track (in priority order),
   - `ROTATOR_IP` to where rotctld is running (default `127.0.0.1` works with `network_mode: host`),
   - the `devices:` entry if you have a GPS on a different path, or remove it entirely if you don't.

3. Build and run:
   ```bash
   docker compose up -d --build
   ```

4. Tail the logs:
   ```bash
   docker compose logs -f
   ```

To change configuration, edit `docker-compose.yml` and `docker compose up -d` again — no rebuild needed unless the source changed.

### Notes on the Docker setup

- **`network_mode: host`** is used so that `rotctld` at `127.0.0.1:4533` on the host is reachable from inside the container, and so the Horus UDP listener binds directly on the host interface. This means the port chosen via `HORUS_UDP_PORT` must be free on the host.
- **GPS passthrough**: `/dev/ttyUSB0` is mapped through `devices:`. If your GPS enumerates as a different path (or you've set up a `/dev/serial/by-id/...` symlink — recommended for stability), update the mapping and `GPS_DEVICE` accordingly.
- **No GPS?** Delete the `devices:` block and unset `GPS_DEVICE`. The station position will stay fixed at `STATION_LAT`/`STATION_LON`/`STATION_ALT`.

---

## Quick start: Native Python

1. Clone the repo and create a venv:
   ```bash
   git clone https://github.com/<you>/horus-rotator.git
   cd horus-rotator
   python3 -m venv venv
   venv/bin/pip install -r requirements.txt
   ```

2. Edit [start_sh.sh](start_sh.sh) — set `--lat`, `--lon`, `--callsigns`, `--gps`, and `--port` to suit your station.

3. Run it:
   ```bash
   chmod +x start_sh.sh
   ./start_sh.sh
   ```

Or invoke directly:
```bash
venv/bin/python3 horus_rotator.py \
    --rotator_ip 127.0.0.1 --rotator_port 4533 \
    --lat 38.0932 --lon -97.9179 \
    --callsigns K5RWK KE5GDB \
    --port 55673 --verbose
```

---

## Configuration reference

All options can be set via CLI flag (native use) or environment variable (Docker). Anything left unset uses the default below.

| CLI flag                       | Env var (Docker)             | Default      | Description |
|-------------------------------|------------------------------|--------------|-------------|
| `--port`                      | `HORUS_UDP_PORT`             | `55672`      | UDP port for Horus payload summaries |
| `--rotator_ip`                | `ROTATOR_IP`                 | `localhost`  | Hostname/IP of the rotctld instance |
| `--rotator_port`              | `ROTATOR_PORT`               | `4533`       | TCP port of rotctld |
| `--rotator_update_threshold`  | `ROTATOR_UPDATE_THRESHOLD`   | `5`          | Minimum azimuth/elevation change (deg) before sending a new command |
| `--rotator_update_rate`       | `ROTATOR_UPDATE_RATE`        | `10`         | How often (s) the rotator update loop runs |
| `--callsigns`                 | `CALLSIGNS`                  | *(empty)*    | Space-separated priority list. Empty = track any callsign |
| `--timeout`                   | `CALLSIGN_TIMEOUT`           | `60`         | Seconds before a higher-priority callsign is considered "silent" |
| `--lat`                       | `STATION_LAT`                | `0.0`        | Station latitude (north positive). Overridden by GPS if `GPS_DEVICE` is set |
| `--lon`                       | `STATION_LON`                | `0.0`        | Station longitude (east positive). Overridden by GPS if `GPS_DEVICE` is set |
| `--alt`                       | `STATION_ALT`                | `0.0`        | Station altitude (m AMSL). Overridden by GPS if `GPS_DEVICE` is set |
| `--gps`                       | `GPS_DEVICE`                 | *(none)*     | Serial device path of a NMEA GPS receiver. Omit for fixed station |
| `--baudrate`                  | `GPS_BAUDRATE`               | `38400`      | GPS baudrate (ignored for u-blox USB) |
| `--verbose` / `-v`            | `VERBOSE`                    | off          | Enable debug logging. Truthy values: `1`, `true`, `yes` |

---

## Callsign priority and timeout

Without `--callsigns`, the rotator tracks whatever payload it hears first — fine if only one balloon is up.

With `--callsigns CALL_A CALL_B CALL_C` (highest priority first), the rules are:

1. **The first callsign in the list always wins** when it transmits.
2. A **lower-priority** callsign is accepted only if **every higher-priority callsign** has been silent for at least `--timeout` seconds.
3. Callsigns **below** the received one's priority never block — they're ignored for the decision.
4. A callsign **not** in the list is accepted only if *every* listed callsign has been silent for at least `--timeout` seconds.
5. At startup, each callsign's "last heard" timestamp is seeded `timeout` seconds in the past, so the first listed payload that actually transmits will grab the rotator immediately — useful when the highest-priority payload may not be flying that day.

### Example

`--callsigns WENET MAIN BACKUP --timeout 30`

| Event                              | Accepted? | Why |
|------------------------------------|-----------|-----|
| `WENET` packet                     | Yes       | Priority 0 always wins |
| `MAIN` packet, `WENET` 5s ago      | No        | `WENET` silent < 30s |
| `MAIN` packet, `WENET` 35s ago     | Yes       | `WENET` silent ≥ 30s |
| `BACKUP` packet, `MAIN` 5s ago     | No        | `MAIN` silent < 30s |
| `BACKUP` packet, all silent > 30s  | Yes       | Both higher-priority quiet |
| `RANDOM` packet, `MAIN` 5s ago     | No        | Unknown callsign blocked by any listed activity |
| `RANDOM` packet, all silent > 30s  | Yes       | Every listed callsign has timed out |

---

## Troubleshooting

**rotctld unreachable from the container**
With `network_mode: host`, `127.0.0.1` inside the container is the same as on the host — confirm `rotctld` is actually listening (`ss -tnlp | grep 4533`). Without host networking, you'd need to point `ROTATOR_IP` at the host's LAN IP or `host.docker.internal` (Docker Desktop only).

**GPS not detected in the container**
Verify the device exists on the host (`ls -l /dev/ttyUSB0`) and that the `devices:` mapping in `docker-compose.yml` matches. On some systems you'll also need to add the host user to the `dialout` group, or run with `--privileged` if udev rules are non-trivial. Prefer `/dev/serial/by-id/...` paths to avoid surprises when other USB devices are plugged in.

**"Port already in use" on the UDP listener**
With `network_mode: host`, `HORUS_UDP_PORT` is bound on the host. Make sure no other Horus consumer (e.g. another instance of horus-gui or chasemapper) is listening on the same port.

**A payload is being received but the rotator never moves**
Check the log — payload summary lines will say `usable` or `discarded`. If `discarded`, the callsign is being filtered out by the priority/timeout logic. Either add the callsign to `CALLSIGNS`, raise its priority, or shorten `CALLSIGN_TIMEOUT`.

**Rotator twitches constantly**
Increase `ROTATOR_UPDATE_THRESHOLD` (degrees) and/or `ROTATOR_UPDATE_RATE` (seconds) so small bearing changes don't trigger commands.

---

## Acknowledgements

- The `listeners.py`, `gps.py`, `rotator.py`, and `earthmaths.py` modules are adapted from Mark Jessop's (VK5QI) work in [horuslib](https://github.com/projecthorus/horuslib) and [radiosonde_auto_rx](https://github.com/projecthorus/radiosonde_auto_rx).
- Project Horus and the Horus UDP payload summary format — <https://github.com/projecthorus>.