"""TcpBrainstem — the previously-untested production transport."""

from __future__ import annotations

import asyncio
import json

import pytest

from brain.transport import TcpBrainstem


async def _mock_tcp_brainstem(handler):
    """Start a mock TCP server, return (host, port, server)."""
    server = await asyncio.start_server(handler, host="127.0.0.1", port=0)
    sockets = server.sockets or []
    host, port = sockets[0].getsockname()[:2]
    return host, port, server


async def test_tcp_connect_send_receive():
    async def handler(reader, writer):
        while not reader.at_eof():
            line = await reader.readline()
            if not line:
                break
            try:
                cmd = json.loads(line)
            except json.JSONDecodeError:
                continue
            resp = json.dumps({"t": "ack", "c": cmd.get("c"), "ok": True}) + "\n"
            writer.write(resp.encode())
            await writer.drain()
        writer.close()

    host, port, server = await _mock_tcp_brainstem(handler)
    try:
        tcp = TcpBrainstem(host=host, port=port)
        await tcp.start()
        # Use a raw brain command; transport calls translate() internally.
        from brain import validator as V
        val = V.Validator()
        cmd = val.validate({"v": 1, "behavior": "neutral", "params": {}})
        responses = await tcp.send(cmd)
        assert len(responses) >= 1
        assert responses[0]["t"] == "ack"
        assert responses[0]["ok"] is True
        await tcp.stop()
    finally:
        server.close()
        await server.wait_closed()


async def test_tcp_filters_telemetry():
    """Server sends a telemetry line before the ack — TcpBrainstem must skip it."""
    async def handler(reader, writer):
        while not reader.at_eof():
            line = await reader.readline()
            if not line:
                break
            # Send telemetry first, then ack.
            telemetry = json.dumps({"t": "telemetry", "p": [2048, 2048, 2048, 2048]}) + "\n"
            writer.write(telemetry.encode())
            ack = json.dumps({"t": "ack", "c": "pose", "ok": True}) + "\n"
            writer.write(ack.encode())
            await writer.drain()
        writer.close()

    host, port, server = await _mock_tcp_brainstem(handler)
    try:
        tcp = TcpBrainstem(host=host, port=port)
        await tcp.start()
        from brain import validator as V
        cmd = V.Validator().validate({"v": 1, "behavior": "neutral", "params": {}})
        responses = await tcp.send(cmd)
        assert len(responses) == 1
        assert responses[0]["t"] == "ack"
        await tcp.stop()
    finally:
        server.close()
        await server.wait_closed()


async def test_tcp_send_raw():
    async def handler(reader, writer):
        while not reader.at_eof():
            line = await reader.readline()
            if not line:
                break
            resp = json.dumps({"t": "status", "p": [2048, 2048, 2048, 2048], "v": 75}) + "\n"
            writer.write(resp.encode())
            await writer.drain()
        writer.close()

    host, port, server = await _mock_tcp_brainstem(handler)
    try:
        tcp = TcpBrainstem(host=host, port=port)
        await tcp.start()
        responses = await tcp.send_raw({"c": "status"})
        assert len(responses) == 1
        assert responses[0]["t"] == "status"
        assert len(responses[0]["p"]) == 4
        await tcp.stop()
    finally:
        server.close()
        await server.wait_closed()
