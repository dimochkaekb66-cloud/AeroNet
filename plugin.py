#!/usr/bin/env python3
"""AeroNet bridge for Microsoft Flight Simulator 2020.

Reads the user aircraft through Python-SimConnect and broadcasts telemetry
as JSON over a WebSocket server bound to 127.0.0.1:8787.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import re
import time
from typing import Any

from SimConnect import AircraftRequests, Request, SimConnect
from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed

HOST = "127.0.0.1"
PORT = 8787
POLL_INTERVAL_SECONDS = 1.0
STALE_AFTER_SECONDS = 4.0
RECONNECT_DELAY_SECONDS = 4.0

# Allow the published AeroNet page, file:// previews, and local development.
# The server binds only to loopback; it isn't exposed to the local network.
ALLOWED_ORIGINS = [
    "https://dimochkaekb66-cloud.github.io",
    re.compile(r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"),
    "null",  # file:// pages
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("AeroNetBridge")

clients: set[Any] = set()
simulator_online = False
simulator_message = "Waiting for Microsoft Flight Simulator…"


class SimConnectUnavailable(RuntimeError):
    """Raised when SimConnect has disconnected or quit."""


def open_simconnect():
    """Create the SimConnect connection and request objects.

    Python-SimConnect needs the Microsoft Flight Simulator SimConnect DLL.
    _time=0 disables the library's value cache so each poll reads fresh data.
    """
    sim = SimConnect()
    requests = AircraftRequests(sim, _time=0, _attemps=4)

    # ATC ID is a string SimVar. It isn't included in every version of the
    # Python-SimConnect built-in request catalogue, so define it explicitly.
    callsign_request = Request(
        (b"ATC ID", b"String"),
        sim,
        _dec="Aircraft callsign / ATC ID",
        _time=0,
        _attemps=4,
    )
    return sim, requests, callsign_request


def read_sim_telemetry(sim, requests, callsign_request, state):
    """Read one fresh telemetry sample; return None while no active flight."""
    if sim.quit:
        raise SimConnectUnavailable("SimConnect reported that MSFS has quit")

    # Python-SimConnect updates this flag from SimStart / SimStop events.
    # If we have seen a flight start and then receive SimStop, stop reporting
    # the aircraft immediately. If the script starts mid-flight, valid SimVars
    # can still be read even before the first observed SimStart event.
    if sim.running:
        state["seen_running"] = True
    elif state["seen_running"]:
        return None

    latitude = requests.get("PLANE LATITUDE")
    longitude = requests.get("PLANE LONGITUDE")
    altitude_ft = requests.get("PLANE ALTITUDE")
    heading_radians = requests.get("PLANE HEADING DEGREES TRUE")
    groundspeed_kts = requests.get("GROUND VELOCITY")

    required = (latitude, longitude, altitude_ft, heading_radians, groundspeed_kts)
    if any(value is None for value in required):
        return None

    values = [float(value) for value in required]
    if not all(math.isfinite(value) for value in values):
        return None

    latitude, longitude, altitude_ft, heading_radians, groundspeed_kts = values
    if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
        return None

    # Python-SimConnect's RequestList declares PLANE_HEADING_DEGREES_TRUE in
    # radians, despite the SimVar name. AeroNet expects degrees.
    heading_degrees = math.degrees(heading_radians) % 360.0

    callsign_value = callsign_request.value
    if isinstance(callsign_value, bytes):
        callsign = callsign_value.decode("utf-8", errors="replace").strip("\x00 \t\r\n")
    elif callsign_value is None:
        callsign = ""
    else:
        callsign = str(callsign_value).strip()

    if not callsign or callsign.lower() in {"none", "unknown"}:
        callsign = "N/A"

    return {
        "latitude": latitude,
        "longitude": longitude,
        "altitude_ft": altitude_ft,
        "heading": heading_degrees,
        "groundspeed_kts": groundspeed_kts,
        "callsign": callsign,
        "timestamp": time.time(),
    }


async def broadcast(payload: dict[str, Any]) -> None:
    """Send a JSON message to all connected AeroNet browser tabs."""
    if not clients:
        return

    message = json.dumps(payload, ensure_ascii=False, allow_nan=False)
    stale_clients = []
    for websocket in tuple(clients):
        try:
            await websocket.send(message)
        except ConnectionClosed:
            stale_clients.append(websocket)
        except Exception:
            log.exception("Failed to send telemetry to a WebSocket client")
            stale_clients.append(websocket)

    for websocket in stale_clients:
        clients.discard(websocket)


async def set_simulator_status(online: bool, message: str) -> None:
    """Update global bridge status and notify browser clients on changes."""
    global simulator_online, simulator_message
    changed = simulator_online != online or simulator_message != message
    simulator_online = online
    simulator_message = message
    if changed:
        await broadcast({
            "type": "status",
            "connected": simulator_online,
            "message": simulator_message,
        })
        log.info(simulator_message)


async def websocket_handler(websocket) -> None:
    """Register a browser client and keep it open until it disconnects."""
    clients.add(websocket)
    try:
        await websocket.send(json.dumps({
            "type": "status",
            "connected": simulator_online,
            "message": simulator_message,
        }, ensure_ascii=False))
        await websocket.wait_closed()
    finally:
        clients.discard(websocket)
        log.info("AeroNet browser disconnected (%d client(s) left)", len(clients))


def close_simconnect(sim) -> None:
    if sim is None:
        return
    try:
        sim.exit()
    except Exception:
        log.debug("SimConnect cleanup raised an exception", exc_info=True)


async def simulator_loop() -> None:
    """Connect/reconnect to MSFS and publish one sample approximately per second."""
    sim = None
    requests = None
    callsign_request = None
    state = {"seen_running": False}
    last_good_sample = 0.0

    while True:
        if sim is None:
            try:
                log.info("Connecting to Microsoft Flight Simulator via SimConnect…")
                sim, requests, callsign_request = await asyncio.to_thread(open_simconnect)
                state = {"seen_running": False}
                last_good_sample = 0.0
                log.info("SimConnect link opened; waiting for live aircraft data…")
            except Exception as exc:
                await set_simulator_status(False, f"MSFS unavailable — retrying: {exc}")
                await asyncio.sleep(RECONNECT_DELAY_SECONDS)
                continue

        try:
            telemetry = await asyncio.to_thread(
                read_sim_telemetry, sim, requests, callsign_request, state
            )

            if telemetry is not None:
                last_good_sample = time.monotonic()
                await set_simulator_status(True, "MSFS connected · live telemetry received")
                await broadcast({"type": "aircraft", "payload": telemetry})
            else:
                # SimStop is reported by Python-SimConnect after a flight ends.
                if state["seen_running"] and not sim.running:
                    await set_simulator_status(False, "MSFS flight stopped · aircraft marker removed")
                    last_good_sample = 0.0
                elif simulator_online and last_good_sample:
                    if time.monotonic() - last_good_sample > STALE_AFTER_SECONDS:
                        await set_simulator_status(False, "MSFS telemetry lost · aircraft marker removed")
                        last_good_sample = 0.0

            if sim.quit:
                raise SimConnectUnavailable("MSFS process closed")

        except SimConnectUnavailable as exc:
            log.warning("%s", exc)
            await set_simulator_status(False, "MSFS disconnected · aircraft marker removed")
            await asyncio.to_thread(close_simconnect, sim)
            sim = requests = callsign_request = None
            state = {"seen_running": False}
            last_good_sample = 0.0
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)

        except Exception as exc:
            log.exception("SimConnect telemetry read failed")
            await set_simulator_status(False, f"SimConnect error · aircraft marker removed: {exc}")
            await asyncio.to_thread(close_simconnect, sim)
            sim = requests = callsign_request = None
            state = {"seen_running": False}
            last_good_sample = 0.0
            await asyncio.sleep(RECONNECT_DELAY_SECONDS)

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def main() -> None:
    log.info("Starting AeroNet WebSocket bridge at ws://%s:%d", HOST, PORT)
    log.info("Open AeroNet in your browser and press Connect in the MSFS telemetry panel")

    async with serve(
        websocket_handler,
        HOST,
        PORT,
        origins=ALLOWED_ORIGINS,
        ping_interval=15,
        ping_timeout=15,
        close_timeout=3,
        max_size=65536,
    ):
        try:
            await simulator_loop()
        finally:
            await set_simulator_status(False, "AeroNet bridge stopped · aircraft marker removed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bridge stopped by user")
