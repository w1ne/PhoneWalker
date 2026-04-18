"""Transports that ship wire-format commands to a brainstem.

Three options:

* ``SubprocessBrainstem`` — spawns ``firmware/simulation/sim.py`` and talks to
  it over stdin/stdout. This is the real integration target for tests; the sim
  is a physically-faithful PyBullet twin of the robot.
* ``SerialBrainstem`` — for a real ESP32 on USB (stub; wire up when needed).
* ``StdoutBrainstem`` — prints to stdout for ad-hoc experimentation.

The WebSocket variant in the earlier draft is deferred. Phone-to-ESP32 WiFi is
a firmware-side feature that isn't landed yet; the sim's stdin/stdout matches
what the firmware's serial bridge speaks today, which is the honest target.
"""

from __future__ import annotations

import asyncio
import collections
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MAX_RECEIVED_LOG = 200

from brain.wire import WireWarning, translate

log = logging.getLogger("brain.transport")


class Brainstem:
    async def start(self) -> None: ...
    async def send(self, command: dict[str, Any]) -> list[dict[str, Any]]: ...
    async def send_raw(self, wire_msg: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError(f"{type(self).__name__} does not support send_raw")
    async def stop(self) -> None: ...


# ------------------------------------------------------------ subprocess sim


@dataclass
class SubprocessBrainstem(Brainstem):
    """Talks to firmware/simulation/sim.py over stdin/stdout."""

    sim_path: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[1]
        / "firmware"
        / "simulation"
        / "sim.py"
    )
    python: str = sys.executable
    gui: bool = False
    _proc: asyncio.subprocess.Process | None = None
    received: collections.deque = field(default_factory=lambda: collections.deque(maxlen=MAX_RECEIVED_LOG))

    async def start(self) -> None:
        args = [self.python, "-u", str(self.sim_path)]
        if self.gui:
            args.append("--gui")
        env = os.environ.copy()
        env.setdefault("PYTHONUNBUFFERED", "1")
        self._proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            await asyncio.wait_for(self._read_until({"t": "ready"}), timeout=15.0)
        except asyncio.TimeoutError:
            raise RuntimeError("sim did not send ready within 15s — crashed?")

    async def send(self, command: dict[str, Any]) -> list[dict[str, Any]]:
        """Send one brain command. Returns the firmware responses (usually 1)."""
        assert self._proc is not None and self._proc.stdin is not None
        result = translate(command)
        for warning in result.warnings:
            log.warning("wire drop: %s", warning)
        responses = []
        for msg in result.messages:
            line = json.dumps(msg) + "\n"
            self._proc.stdin.write(line.encode())
            await self._proc.stdin.drain()
            resp = await self._read_one_ack()
            if resp is not None:
                responses.append(resp)
                self.received.append(resp)
        return responses

    async def send_raw(self, wire_msg: dict[str, Any]) -> list[dict[str, Any]]:
        """Send a raw wire command, accepting ack/err/status responses."""
        assert self._proc is not None and self._proc.stdin is not None
        line = json.dumps(wire_msg) + "\n"
        self._proc.stdin.write(line.encode())
        await self._proc.stdin.drain()
        resp = await self._read_one_response(("ack", "err", "status"))
        return [resp] if resp is not None else []

    async def _read_one_response(
        self, accept: tuple[str, ...] = ("ack", "err"),
    ) -> dict[str, Any] | None:
        assert self._proc is not None and self._proc.stdout is not None
        for _ in range(50):
            line = await self._proc.stdout.readline()
            if not line:
                return None
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("t") in accept:
                return msg
        return None

    async def stop(self) -> None:
        if self._proc is None:
            return
        try:
            if self._proc.stdin is not None and not self._proc.stdin.is_closing():
                self._proc.stdin.close()
        except (BrokenPipeError, ConnectionResetError):
            pass
        try:
            await asyncio.wait_for(self._proc.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            self._proc.kill()
            await self._proc.wait()
        self._proc = None

    async def _read_until(self, match: dict[str, Any]) -> dict[str, Any]:
        assert self._proc is not None and self._proc.stdout is not None
        while True:
            line = await self._proc.stdout.readline()
            if not line:
                raise RuntimeError("sim closed stdout before ready")
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if all(msg.get(k) == val for k, val in match.items()):
                return msg

    async def _read_one_ack(self) -> dict[str, Any] | None:
        """Read lines until we see an ack/err. Telemetry lines are skipped."""
        assert self._proc is not None and self._proc.stdout is not None
        for _ in range(50):
            line = await self._proc.stdout.readline()
            if not line:
                return None
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("t") in ("ack", "err"):
                return msg
        return None


# ------------------------------------------------------------ stdout


# ------------------------------------------------------------ tcp


@dataclass
class TcpBrainstem(Brainstem):
    """Talks to a brainstem listening on TCP (JSON lines).

    Use this when the brain runs on one device (e.g. a Pixel in Termux)
    and the robot/sim runs elsewhere. Pair with ``tools/sim_server.py``
    on the sim side, or eventually a WiFi-enabled ESP32.
    """

    host: str = "127.0.0.1"
    port: int = 8765
    _reader: asyncio.StreamReader | None = None
    _writer: asyncio.StreamWriter | None = None
    received: collections.deque = field(default_factory=lambda: collections.deque(maxlen=MAX_RECEIVED_LOG))

    async def start(self) -> None:
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
        log.info("connected to brainstem tcp://%s:%d", self.host, self.port)

    async def send(self, command: dict[str, Any]) -> list[dict[str, Any]]:
        assert self._writer is not None and self._reader is not None
        result = translate(command)
        for warning in result.warnings:
            log.warning("wire drop: %s", warning)
        responses = []
        for msg in result.messages:
            line = json.dumps(msg) + "\n"
            self._writer.write(line.encode())
            await self._writer.drain()
            resp = await self._read_one_ack()
            if resp is not None:
                responses.append(resp)
                self.received.append(resp)
        return responses

    async def _read_one_ack(self) -> dict[str, Any] | None:
        """Read lines until we see an ack/err, skipping telemetry."""
        assert self._reader is not None
        for _ in range(50):
            resp_line = await self._reader.readline()
            if not resp_line:
                return None
            try:
                msg = json.loads(resp_line)
            except json.JSONDecodeError:
                continue
            if msg.get("t") in ("ack", "err"):
                return msg
        return None

    async def send_raw(self, wire_msg: dict[str, Any]) -> list[dict[str, Any]]:
        assert self._writer is not None and self._reader is not None
        self._writer.write((json.dumps(wire_msg) + "\n").encode())
        await self._writer.drain()
        resp = await self._read_one_response(("ack", "err", "status"))
        return [resp] if resp is not None else []

    async def _read_one_response(
        self, accept: tuple[str, ...] = ("ack", "err"),
    ) -> dict[str, Any] | None:
        assert self._reader is not None
        for _ in range(50):
            resp_line = await self._reader.readline()
            if not resp_line:
                return None
            try:
                msg = json.loads(resp_line)
            except json.JSONDecodeError:
                continue
            if msg.get("t") in accept:
                return msg
        return None

    async def stop(self) -> None:
        if self._writer is not None:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
        self._reader = None
        self._writer = None


@dataclass
class StdoutBrainstem(Brainstem):
    received: collections.deque = field(default_factory=lambda: collections.deque(maxlen=MAX_RECEIVED_LOG))

    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    async def send(self, command: dict[str, Any]) -> list[dict[str, Any]]:
        result = translate(command)
        for warning in result.warnings:
            print(f"wire drop: {warning}")
        for msg in result.messages:
            print(f"wire → {json.dumps(msg)}")
            self.received.append(msg)
        return [{"t": "ack", "c": m.get("c"), "ok": True} for m in result.messages]
