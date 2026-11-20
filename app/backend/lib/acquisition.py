"""Read-only ioBroker/MQTT/Modbus TCP adapters, shared by live view and recorder."""
import asyncio
import json
import math
import struct
import time
import threading
from collections import defaultdict
from lib.db import db
from models.acquisition import Connection, Measurement

_mqtt = {}
_mqtt_lock = threading.Lock()
_read_lock = asyncio.Lock()
_last_read = 0.0
_last_result = ({}, [], {})


def numeric(value):
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return float(value.lower() == "true")
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def decode_payload(payload, path):
    value = payload.decode("utf-8")
    if path:
        value = json.loads(value)
        for key in path.split("."):
            value = value[int(key)] if isinstance(value, list) else value[key]
    return numeric(value)


def decode_registers(payload, point):
    words = [payload[i:i+2] for i in range(0, len(payload), 2)]
    if point.word_order == "little":
        words.reverse()
    if point.byte_order == "little":
        words = [w[::-1] for w in words]
    fmt = {"uint16": "H", "int16": "h", "uint32": "I", "int32": "i", "float32": "f", "float64": "d"}[point.datatype]
    return numeric(struct.unpack(">" + fmt, b"".join(words))[0])


async def read_modbus(connection, points):
    """One TCP session per connection; only FC03/04, with exact MBAP validation."""
    result = {}
    reader, writer = await asyncio.wait_for(asyncio.open_connection(connection.host, connection.port), connection.timeout_s)
    try:
        for transaction, point in enumerate(points, 1):
            count = {"uint16": 1, "int16": 1, "uint32": 2, "int32": 2, "float32": 2, "float64": 4}[point.datatype]
            if point.register_address + count > 65536:
                raise ValueError("Registerbereich überschritten")
            writer.write(struct.pack(">HHHBBHH", transaction, 0, 6, point.unit_id, point.function, point.register_address, count))
            await writer.drain()
            header = await asyncio.wait_for(reader.readexactly(7), connection.timeout_s)
            tx, protocol, length, unit = struct.unpack(">HHHB", header)
            if tx != transaction or protocol != 0 or unit != point.unit_id or not 2 <= length <= 254:
                raise ValueError("Ungültiger Modbus-Antwortkopf")
            pdu = await asyncio.wait_for(reader.readexactly(length - 1), connection.timeout_s)
            if pdu[0] == point.function | 0x80 and len(pdu) == 2:
                result[point.id] = None
                continue
            if pdu[0] != point.function or pdu[1] != count * 2 or len(pdu) != count * 2 + 2:
                raise ValueError(f"Modbus-Fehler bei Register {point.register_address}: {pdu.hex()}")
            result[point.id] = decode_registers(pdu[2:], point)
    finally:
        writer.close()
        await writer.wait_closed()
    return result


def mqtt_read(connection, points):
    import paho.mqtt.client as mqtt
    signature = connection.model_dump_json() + json.dumps(sorted(p.address for p in points))
    entry = _mqtt.get(connection.id)
    if entry is None or entry[0] != signature:
        if entry:
            entry[1].disconnect()
            entry[1].loop_stop()
        cache = {}
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="energieboard-" + connection.id)
        if connection.username:
            client.username_pw_set(connection.username, connection.password)
        if connection.tls:
            client.tls_set()
        def connected(client, userdata, flags, reason, properties):
            if reason == 0:
                for topic in sorted({p.address for p in points}):
                    client.subscribe(topic, qos=1)
        def received(client, userdata, message):
            with _mqtt_lock:
                cache[message.topic] = (message.payload, time.time(), message.retain)
        def disconnected(client, userdata, flags, reason, properties):
            with _mqtt_lock:
                cache.clear()
        client.on_connect, client.on_message, client.on_disconnect = connected, received, disconnected
        client.connect_async(connection.host, connection.port, keepalive=30)
        client.loop_start()
        entry = _mqtt[connection.id] = (signature, client, cache)
    out, status = {}, {}
    for point in points:
        with _mqtt_lock:
            sample = entry[2].get(point.address)
        value = None
        stamp = None
        retained = False
        if sample:
            payload, stamp, retained = sample
            if time.time() - stamp <= point.stale_s:
                try:
                    value = decode_payload(payload, point.json_path)
                except (ValueError, KeyError, IndexError, TypeError, UnicodeError):
                    pass
        out[point.id] = value
        status[point.id] = {"received_at": stamp, "retained": retained}
    return out, status


async def close_connections():
    for _, client, _ in list(_mqtt.values()):
        client.disconnect()
        await asyncio.to_thread(client.loop_stop)
    _mqtt.clear()


async def read_measurements(settings, force=False):
    global _last_read, _last_result
    async with _read_lock:
        if not force and time.monotonic() - _last_read < 1:
            return _last_result
        connections = [Connection(**d) for d in await db.connections.find({}, {"_id": 0}).to_list()]
        points = [Measurement(**d) for d in await db.measurements.find({}, {"_id": 0}).to_list()]
        groups = defaultdict(list)
        for point in points:
            if point.enabled:
                groups[point.connection_id].append(point)
        active_mqtt = {c.id for c in connections if c.enabled and c.protocol == "mqtt" and groups.get(c.id)}
        for id in list(_mqtt):
            if id not in active_mqtt:
                _, client, _ = _mqtt.pop(id)
                client.disconnect()
                await asyncio.to_thread(client.loop_stop)
        values, errors, states = {}, [], {}
        from lib.sources import iob_get_bulk
        semaphore = asyncio.Semaphore(8)
        async def fetch(connection, group):
            raw, statuses = {}, {}
            failures = []
            try:
                if connection.protocol == "mqtt":
                    raw, statuses = await asyncio.to_thread(mqtt_read, connection, group)
                elif connection.protocol == "modbus":
                    raw = await read_modbus(connection, group)
                else:
                    s = settings.model_copy(deep=True)
                    s.iobroker.host, s.iobroker.port = connection.host, connection.port
                    s.iobroker.protocol = "https" if connection.tls else "http"
                    s.iobroker.timeout_s = connection.timeout_s
                    data = await iob_get_bulk(s, [p.address for p in group])
                    raw = {p.id: data.get(p.address) for p in group}
            except Exception as exc:
                failures.append(f"{connection.name}: {type(exc).__name__}: {exc}")
            return group, raw, statuses, failures
        async def bounded(connection, group):
            async with semaphore:
                return await fetch(connection, group)
        batches = await asyncio.gather(*(bounded(c, groups[c.id]) for c in connections if c.enabled and groups.get(c.id)))
        for group, raw, statuses, failures in batches:
            errors.extend(failures)
            for point in group:
                value = numeric(raw.get(point.id))
                normalized = None if value is None else numeric(value * point.scale + point.offset)
                values["point:" + point.id] = normalized
                states[point.id] = {"raw": value, "value": normalized, "unit": point.unit,
                    **statuses.get(point.id, {"received_at": time.time() if value is not None else None, "retained": False}),
                    "available": normalized is not None}
        _last_read, _last_result = time.monotonic(), (values, errors, states)
        return _last_result


async def read_values(settings, ids):
    from lib.sources import iob_get_bulk
    legacy = [key for key in ids if not key.startswith("point:")]
    values, errors, _ = await read_measurements(settings)
    values = dict(values)
    errors = list(errors)
    if legacy and settings.iobroker.host:
        try:
            values.update(await iob_get_bulk(settings, legacy))
        except Exception as exc:
            errors.append(f"ioBroker: {exc}")
    return values, list(errors)
