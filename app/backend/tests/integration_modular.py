"""Integration against a real MongoDB, API, and local protocol fixtures.
Run with MONGOD_BIN pointing to mongod; optional BROWSER_TEST invokes browser checks.
Fixtures exist only in this test process, never in the shipped application.
"""
import csv
import io
import gzip
import json
import os
import socket
import socketserver
import struct
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote
import httpx
from pymongo import MongoClient
from bson import Binary, Decimal128

ROOT = Path(__file__).resolve().parents[3]
BACKEND = ROOT / "app/backend"


def port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def exact(sock, n):
    out = b""
    while len(out) < n:
        part = sock.recv(n-len(out))
        if not part:
            raise EOFError()
        out += part
    return out


values = {"legacy": 125, "grid": 500, "a": 1000, "b": 600, "motor": 300, "pv": 200,
          "bat1": 1000, "soc1": 80, "bat2": 500, "soc2": 20, "mppt": 1500, "hybrid": 750, "run": 1,"idle":0,"engine_temperature":86,"efficiency":80,"fuel_consumption":2.3,"operating_hours":1234,"reserve":30}


class IoBroker(BaseHTTPRequestHandler):
    def do_GET(self):
        ids = unquote(self.path.split("/getBulk/")[-1]).split(",")
        payload = json.dumps([{"id": id, "val": values.get(id)} for id in ids]).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers()
        self.wfile.write(payload)
    def log_message(self, *args):
        pass


class MQTT(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            while True:
                kind = exact(self.request, 1)[0]
                length, mult = 0, 1
                while True:
                    v = exact(self.request, 1)[0]; length += (v & 127) * mult; mult *= 128
                    if not v & 128: break
                body = exact(self.request, length)
                if kind >> 4 == 1: self.request.sendall(b"\x20\x02\x00\x00")
                elif kind >> 4 == 8:
                    self.request.sendall(b"\x90\x03" + body[:2] + b"\x01")
                    topic_len = int.from_bytes(body[2:4], "big")
                    topic = body[4:4+topic_len]
                    payload = b'{"data":{"power":432.5}}'
                    packet = struct.pack(">H", len(topic)) + topic + payload
                    self.request.sendall(bytes([0x31, len(packet)]) + packet)
                elif kind >> 4 == 12: self.request.sendall(b"\xd0\x00")
                elif kind >> 4 == 14: break
        except (EOFError, OSError):
            pass


class Modbus(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            while True:
                request = exact(self.request, 12)
                tx, _, _, unit, fc, register, count = struct.unpack(">HHHBBHH", request)
                data = struct.pack(">f", 250.5) if count == 2 else struct.pack(">H", 55)
                self.request.sendall(struct.pack(">HHHBBB", tx, 0, len(data)+3, unit, fc, len(data)) + data)
        except (EOFError, OSError): pass


class TCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    mongo_port, api_port = port(), port()
    token = uuid.uuid4().hex
    database = "energieboard_integration_" + uuid.uuid4().hex[:8]
    ROOT.joinpath("work").mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="modular-", dir=ROOT/"work") as temporary:
        temporary = Path(temporary)
        mongo_log = (temporary/"mongo.log").open("w")
        mongo = subprocess.Popen([os.environ["MONGOD_BIN"], "--dbpath", str(temporary), "--port", str(mongo_port), "--bind_ip", "127.0.0.1", "--wiredTigerCacheSizeGB", "0.25"], stdout=mongo_log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        uri = f"mongodb://127.0.0.1:{mongo_port}"
        client = MongoClient(uri, serverSelectionTimeoutMS=500)
        api = None
        fixtures = [ThreadingHTTPServer(("127.0.0.1",0),IoBroker), TCPServer(("127.0.0.1",0),MQTT), TCPServer(("127.0.0.1",0),Modbus)]
        try:
            for _ in range(60):
                try: client.admin.command("ping"); break
                except Exception: time.sleep(.2)
            client.admin.command("ping")
            for fixture in fixtures: threading.Thread(target=fixture.serve_forever,daemon=True).start()
            iob_port, mqtt_port, modbus_port = [fixture.server_address[1] for fixture in fixtures]
            db = client[database]
            db.settings.insert_one({"id":"app","iobroker":{"host":"127.0.0.1","port":iob_port},"recorder":{"enabled":False,"interval_s":5}})
            db.flows.insert_one({"id":"legacy","name":"Altbestand","datapoints":{"power_total":"legacy"},"created_at":datetime.now(timezone.utc),"enabled":True})
            env = {**os.environ,"MONGO_URL":uri,"DB_NAME":database,"TEST_PORT":str(api_port),"TEST_TOKEN":token,"PYTHONPATH":str(BACKEND)}
            log = ROOT.joinpath("work/modular-server.log").open("w",encoding="utf-8")
            api = subprocess.Popen([sys.executable,str(Path(__file__)),"--serve"],env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            base = f"http://127.0.0.1:{api_port}"
            with httpx.Client(base_url=base+"/api",timeout=20) as http:
                for _ in range(80):
                    try:
                        if http.get("/").status_code==200: break
                    except httpx.HTTPError: pass
                    time.sleep(.15)
                http.get("/").raise_for_status()
                def get(path): return http.get(path).raise_for_status().json()
                def put(path,data): return http.put(path,json=data).raise_for_status().json()
                def create(**fields): return http.post("/flows",json=fields).raise_for_status().json()
                old = get("/flows")[0]
                assert old["datapoints"]["power_total"].startswith("point:")
                assert db.measurements.find_one({"history_key":"legacy"})
                assert not get("/live")["grid_configured"]
                connection = get("/connections")[0]
                def point(id,address,unit="W",**fields):
                    return put("/measurements/"+id,{"name":id,"connection_id":connection["id"],"address":address,"unit":unit,**fields})
                for key in values: point(key,key,"%" if key.startswith("soc") else "W")
                grid = create(name="Netzanschluss",category="grid",grid_mode="signed",datapoints={"power_total":"point:grid"})
                assert grid["kind"]=="grid"
                create(name="BHKW",category="generator",direction="in",icon="generator",datapoints={"power_total":"point:pv","engine_temperature":"point:engine_temperature","efficiency":"point:efficiency","fuel_consumption":"point:fuel_consumption","operating_hours":"point:operating_hours"})
                idle=create(name="Nullgerät",datapoints={"power_total":"point:idle"})
                a = create(name="Haus",kind="node",datapoints={"power_total":"point:a"})
                b = create(name="Werkstatt",kind="node",parent_id=a["id"],datapoints={"power_total":"point:b"})
                create(name="Motor",parent_id=b["id"],datapoints={"power_total":"point:motor"})
                create(name="Dach PV",category="pv",direction="in",parent_id=b["id"],datapoints={"power_total":"point:pv"})
                create(name="RUN-Pumpe",run_power_w=200,datapoints={"run":"point:run"})
                bat1 = create(name="Speicher A",kind="storage",capacity_kwh=10,reserve_soc_pct=20,parent_id=b["id"],datapoints={"power_total":"point:bat1","soc":"point:soc1"})
                bat2 = create(name="Speicher B",kind="storage",capacity_kwh=5,datapoints={"power_total":"point:bat2","soc":"point:soc2"})
                mppt = create(name="MPPT Garten",category="pv",pv_type="mppt",electrical_side="dc",datapoints={"power_total":"point:mppt"})
                hybrid = create(name="Victron Hybrid",category="pv",pv_type="hybrid",direction="in",storage_ids=[bat1["id"],bat2["id"]],mppt_ids=[mppt["id"]],datapoints={"power_total":"point:hybrid"})
                assert http.put("/flows/"+bat1["id"],json={**bat1,"kind":"device","category":"consumer"}).status_code==409
                assert http.put("/flows/"+mppt["id"],json={**mppt,"pv_type":"wr"}).status_code==409
                assert http.put("/flows/"+a["id"],json={**a,"parent_id":b["id"]}).status_code==422
                assert http.delete("/flows/"+grid["id"]).status_code==409
                assert http.put("/flows/"+grid["id"],json={**grid,"enabled":False}).status_code==409
                assert http.delete("/flows/"+bat1["id"]).status_code==409
                assert http.delete("/measurements/grid").status_code==409
                for protocol,source_port in (("mqtt",mqtt_port),("modbus",modbus_port)):
                    put("/connections/"+protocol,{"name":protocol,"protocol":protocol,"host":"127.0.0.1","port":source_port,"username":"fixture","password":"fixture-secret"})
                    put("/measurements/"+protocol,{"name":protocol,"connection_id":protocol,"address":"test/power","json_path":"data.power","datatype":"float32","stale_s":5})
                assert all(c["password"]=="" for c in get("/connections"))
                for _ in range(20):
                    preview=get("/measurements/live")
                    if preview["states"]["mqtt"]["value"]==432.5: break
                    time.sleep(.2)
                assert preview["states"]["mqtt"]["value"]==432.5,preview
                assert preview["states"]["modbus"]["value"]==250.5,preview
                assert preview["states"]["mqtt"]["retained"]
                live=get("/live")
                assert live["storage_total"]["soc_pct"]==60,live
                assert live["storage_total"]["remaining_kwh"]==9
                assert live["storages"][0]["runtime_h"]==6
                assert not any(f["storage_id"] or f["flow_id"]==mppt["id"] for f in live["flows"])
                assert live["summary"]["pv_w"] is None
                assert next(n for n in live["nodes"] if n["id"]==a["id"])["difference_w"]==400
                assert next(n for n in live["nodes"] if n["id"]==b["id"])["difference_w"]==500
                assert get("/schemas/flow")["properties"]["capacity_kwh"]
                for i in range(50):
                    values[f"load{i}"]=10
                    point(f"load{i}",f"load{i}")
                    create(name=f"Verbraucher {i}",parent_id=b["id"],datapoints={"power_total":f"point:load{i}"})
                # Persisted minute-long zero interval hides only live representation.
                stamp=time.time()
                db.visibility.replace_one({"id":idle["id"]},{"id":idle["id"],"zero_since":stamp-61,"last_seen":stamp},upsert=True)
                assert next(f for f in get("/live")["flows"] if f["flow_id"]==idle["id"])["hidden"]
                values["idle"]=5
                time.sleep(1.05)
                assert not next(f for f in get("/live")["flows"] if f["flow_id"]==idle["id"])["hidden"]
                values["idle"]=0
                # Real CSV preview/apply and stale-preview protection.
                exported=http.get("/config/csv").raise_for_status().text
                assert "fixture-secret" not in exported
                compact=http.get("/config/csv?scope=measurements").raise_for_status().text
                assert "appearance.layout" not in compact and "connection_id" in compact
                assert len(list(csv.DictReader(io.StringIO(http.get("/config/csv?template=true&scope=measurements").raise_for_status().text.lstrip("\ufeff")),delimiter=";")))==0
                csv_request={"csv_text":exported,"mode":"merge"}
                planned=http.post("/config/csv/preview",json=csv_request).raise_for_status().json()
                before=get("/settings");put("/settings",{**before,"site_name":"revision-change"})
                assert http.post("/config/csv/apply",json={**csv_request,"expected_revision":planned["revision"]}).status_code==409
                put("/settings",before)
                planned=http.post("/config/csv/preview",json=csv_request).raise_for_status().json()
                applied=http.post("/config/csv/apply",json={**csv_request,"expected_revision":planned["revision"]}).raise_for_status().json()
                assert db.config_backups.find_one({"id":applied["backup_id"]})
                assert db.connections.find_one({"id":"mqtt"})["password"]=="fixture-secret"
                assert any(f["id"]==grid["id"] for f in get("/flows"))
                print("CSV export/preview/apply, stable IDs, secret preservation and stale preview rejection OK",flush=True)
                settings=get("/settings")
                settings["appearance"]={"layout":"flow","background":"#101216","surface":"#20242B","accent":"#34D399"}
                settings["recorder"]={"enabled":True,"interval_s":5}
                put("/settings",settings)
                for _ in range(40):
                    if db.samples.count_documents({"dp":"point:mqtt"}):break
                    time.sleep(.2)
                assert db.samples.count_documents({"dp":"point:mqtt"})>0
                assert db.samples.count_documents({"dp":f"energieboard:{a['id']}:rest_consumption"})>0
                print("Real HTTP API, MongoDB, MQTT, Modbus TCP, 50 devices, registry, nodes, storage and recorder OK",flush=True)
                if os.environ.get("BROWSER_TEST"):
                    stamp=time.time()
                    db.visibility.update_one({"id":idle["id"]},{"$set":{"last_seen":stamp,"zero_since":stamp-61}},upsert=True)
                    subprocess.run(["node",os.environ["BROWSER_TEST"]],env={**env,"TEST_URL":base},cwd=ROOT,check=True)
                latest=get("/measurements/live")
                stamp=latest["states"]["mqtt"]["received_at"]
                time.sleep(max(0,5.1-(time.time()-stamp)))
                assert not get("/measurements/live")["states"]["mqtt"]["available"]
                put("/flows/"+a["id"],{**a,"enabled":False})
                active=get("/live")
                assert all(n["id"] not in (a["id"],b["id"]) for n in active["nodes"])
                assert all(f["parent_id"] not in (a["id"],b["id"]) for f in active["flows"])
                put("/flows/"+a["id"],a)
                print("MQTT expiry and recursive node disable OK",flush=True)
                # Stop writer before backup and migration roundtrip.
                httpx.post(base+"/__test_stop",headers={"X-Test-Token":token}).raise_for_status()
                api.wait(timeout=15);api=None
                backup=temporary/"backup"
                db.backup_probe.create_index("code", unique=True)
                db.backup_probe.insert_one({"code":"test","binary":Binary(b"\x00\xff"),"decimal":Decimal128("1.25"),"time":datetime.now(timezone.utc)})
                subprocess.run([sys.executable,str(ROOT/"deploy/backup.py"),"backup",str(backup)],env=env,check=True)
                db.settings.update_one({"id":"app"},{"$set":{"site_name":"changed"}})
                subprocess.run([sys.executable,str(ROOT/"deploy/backup.py"),"restore",str(backup)],env=env,check=True)
                assert db.settings.find_one({"id":"app"})["site_name"]!="changed"
                probe=db.backup_probe.find_one({"code":"test"})
                assert probe["binary"]==b"\x00\xff" and probe["decimal"]==Decimal128("1.25")
                assert db.backup_probe.index_information()["code_1"]["unique"]
                count=db.measurements.count_documents({})
                subprocess.run([sys.executable,"-c","import asyncio; from lib.migrations import migrate; from lib.db import client;\nasync def check():\n await migrate(); await migrate(); await client.close()\nasyncio.run(check())"],env=env,cwd=BACKEND,check=True)
                assert db.measurements.count_documents({})==count
                print("Backup/restore including history and repeated configuration migration OK",flush=True)
        finally:
            if api is not None:
                try:httpx.post(f"http://127.0.0.1:{api_port}/__test_stop",headers={"X-Test-Token":token},timeout=3)
                except Exception:api.terminate()
                api.wait(timeout=15)
            for fixture in fixtures:fixture.shutdown();fixture.server_close()
            try: client.admin.command("shutdown",force=True)
            except Exception: pass
            client.close();mongo.wait(timeout=15);mongo_log.close()


if __name__=="__main__":
    if "--serve" in sys.argv:
        sys.path.insert(0,str(BACKEND))
        import uvicorn
        from fastapi import Header, HTTPException
        from server import app
        runner=uvicorn.Server(uvicorn.Config(app,host="127.0.0.1",port=int(os.environ["TEST_PORT"])))
        @app.post("/__test_stop",include_in_schema=False)
        async def stop(x_test_token:str=Header()):
            if x_test_token!=os.environ["TEST_TOKEN"]:raise HTTPException(403)
            runner.should_exit=True
            return {}
        runner.run()
    else:main()
