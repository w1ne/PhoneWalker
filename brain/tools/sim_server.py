"""TCP wrapper around firmware/simulation/sim.py.

Runs on your laptop. The phone-side brain connects over TCP, sends JSON
lines in the firmware wire protocol, reads ack/err lines back. One client
at a time is plenty for a demo.

Usage:
    python3 -m brain.tools.sim_server --host 0.0.0.0 --port 8765
    # phone: python3 -m brain.main --transport tcp --host <laptop-ip>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

log = logging.getLogger("brain.tools.sim_server")

SIM_PATH = Path(__file__).resolve().parents[2] / "firmware" / "simulation" / "sim.py"


async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    peer = writer.get_extra_info("peername")
    log.info("client connected: %s", peer)
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-u", str(SIM_PATH),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    assert proc.stdin is not None and proc.stdout is not None

    # Drain ready banner.
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("t") == "ready":
            break

    try:
        while not reader.at_eof():
            line = await reader.readline()
            if not line:
                break
            text = line.decode().strip()
            if not text:
                continue
            proc.stdin.write((text + "\n").encode())
            await proc.stdin.drain()
            # Forward first ack/err back to client.
            for _ in range(50):
                resp_line = await proc.stdout.readline()
                if not resp_line:
                    break
                try:
                    resp = json.loads(resp_line)
                except json.JSONDecodeError:
                    continue
                if resp.get("t") in ("ack", "err"):
                    writer.write(resp_line)
                    await writer.drain()
                    break
    except (ConnectionResetError, BrokenPipeError):
        pass
    finally:
        log.info("client disconnected: %s", peer)
        try:
            if proc.stdin is not None and not proc.stdin.is_closing():
                proc.stdin.close()
        except Exception:
            pass
        try:
            await asyncio.wait_for(proc.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def main_async(host: str, port: int) -> None:
    server = await asyncio.start_server(handle, host=host, port=port)
    addrs = ", ".join(str(s.getsockname()) for s in (server.sockets or []))
    log.info("sim server listening on %s", addrs)
    async with server:
        await server.serve_forever()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="0.0.0.0")
    p.add_argument("--port", type=int, default=8765)
    args = p.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    asyncio.run(main_async(args.host, args.port))


if __name__ == "__main__":
    main()
