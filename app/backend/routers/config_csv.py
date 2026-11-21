"""Versioned, flattened CSV configuration with full validation and preview."""
import csv
import hashlib
import io
import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from lib.db import db
from lib.config_lock import locked
from models.flow import Flow
from models.acquisition import Connection, Measurement
from models.settings import AppSettings

router = APIRouter(tags=["CSV-Konfiguration"])
MODELS = {"connection":Connection,"measurement":Measurement,"flow":Flow,"settings":AppSettings}
COLLECTIONS = {"connection":"connections","measurement":"measurements","flow":"flows","settings":"settings"}
SECRETS = {"password","token"}
OPTIONAL = {"parent_id","hybrid_id","capacity_kwh","run_power_w","legacy_until"}


def flatten(data, prefix=""):
    result = {}
    for key,value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if key in SECRETS or key == "_id":continue
        if isinstance(value,dict) and key!="extra":result.update(flatten(value,path))
        elif isinstance(value,list):result[path]="|".join(map(str,value))
        elif isinstance(value,dict):result[path]=json.dumps(value,ensure_ascii=False,allow_nan=False)
        elif isinstance(value,datetime):result[path]=value.isoformat()
        else:result[path]=value
    return result


def safe_cell(value):
    if value is None:return ""
    if isinstance(value,bool):return "true" if value else "false"
    # Prevent spreadsheet formulas in string values. Import reverses this prefix.
    if isinstance(value,str) and value.startswith(("=","+","-","@","\t","\r","'")):
        return "'"+value
    return value


def render_csv(state, selected=None):
    rows=[]
    defaults = {"connection":Connection(name="Vorlage",protocol="mqtt",host="localhost",port=1883),
        "measurement":Measurement(name="Vorlage",connection_id=""),"flow":Flow(name="Vorlage"),"settings":AppSettings()}
    headers={"record_type","csv_version","id"}
    for kind,model in defaults.items():
        if selected is None or kind in selected:headers.update(flatten(model.model_dump()))
    for kind,documents in state.items():
        for doc in documents:
            row={"record_type":kind,"csv_version":1,**flatten(doc)}
            headers.update(row);rows.append(row)
    headers=["record_type","csv_version","id"]+sorted(headers-{"record_type","csv_version","id"})
    output=io.StringIO(newline="")
    writer=csv.DictWriter(output,fieldnames=headers,delimiter=";",lineterminator="\n")
    writer.writeheader()
    for row in rows:writer.writerow({k:safe_cell(v) for k,v in row.items()})
    return output.getvalue()


async def snapshot():
    state={}
    for kind,collection in COLLECTIONS.items():
        state[kind]=await db[collection].find({}, {"_id":0}).to_list()
    return state


def revision(state):
    return hashlib.sha256(json.dumps(state,default=str,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def parse_csv(text):
    if len(text.encode("utf-8"))>2_000_000:raise ValueError("CSV ist größer als 2 MB.")
    text=text.lstrip("\ufeff")
    delimiter=";" if ";" in text.splitlines()[0] else ","
    reader=csv.DictReader(io.StringIO(text),delimiter=delimiter)
    if not reader.fieldnames or "record_type" not in reader.fieldnames or len(set(reader.fieldnames))!=len(reader.fieldnames):
        raise ValueError("Eindeutige Spaltenüberschriften einschließlich record_type erforderlich.")
    allowed=set(next(csv.reader(io.StringIO(render_csv({kind:[] for kind in MODELS})),delimiter=";")))
    unknown=set(reader.fieldnames)-allowed
    if unknown:raise ValueError("Unbekannte CSV-Spalten: "+", ".join(sorted(unknown)))
    result={kind:[] for kind in MODELS};seen=set()
    for line,row in enumerate(reader,2):
        if line>5002:raise ValueError("Maximal 5000 Einträge importieren.")
        kind=row.pop("record_type","")
        if kind not in MODELS:raise ValueError(f"Zeile {line}: ungültiger record_type.")
        if row.pop("csv_version","")!="1":raise ValueError(f"Zeile {line}: CSV-Version 1 erforderlich.")
        if None in row:raise ValueError(f"Zeile {line}: zu viele Spalten.")
        data={}
        for path,value in row.items():
            if value is None or value=="":continue
            if any(part in SECRETS for part in path.split(".")):raise ValueError("Passwörter/Tokens werden nicht per CSV importiert.")
            if value.startswith("'") and len(value)>1 and value[1] in "=+-@\t\r'":value=value[1:]
            target=data;parts=path.split(".")
            for part in parts[:-1]:
                if part in target and not isinstance(target[part],dict):raise ValueError("Widersprüchliche Spalten.")
                target=target.setdefault(part,{})
            key=parts[-1]
            if key in ("storage_ids","mppt_ids"):value=[v.strip() for v in value.split("|") if v.strip()]
            elif key=="function":value=int(value)
            elif key=="extra":value=json.loads(value)
            target[key]=value
        id=data.get("id") or ("app" if kind=="settings" else "")
        if not id or not isinstance(id,str) or len(id)>100 or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:" for c in id):raise ValueError(f"Zeile {line}: ungültige ID.")
        data["id"]=id
        if (kind,id) in seen:raise ValueError(f"Zeile {line}: doppelte ID.")
        seen.add((kind,id));result[kind].append(data)
    return result


def prepare(state, text, mode):
    incoming=parse_csv(text);candidate={};changes=[]
    for kind,model in MODELS.items():
        old={d["id"]:d for d in state[kind]}
        merged=dict(old) if mode=="merge" else {}
        for data in incoming[kind]:
            id=data["id"];previous=old.get(id,{})
            # Imported rows are complete records; blank optional cells clear a mapping.
            if kind=="flow":
                for key in OPTIONAL-{"legacy_until"}:data.setdefault(key,None)
            if kind=="measurement":
                for key in ("history_key","legacy_until"):
                    if previous:data[key]=previous.get(key)
            if kind=="connection":data["password"]=previous.get("password","")
            if kind=="settings":
                data.setdefault("influx",{})
                for key in ("password","token"):data["influx"][key]=previous.get("influx",{}).get(key,"")
            if kind=="flow":
                data["schema_version"]=5
                if previous:data["created_at"]=previous.get("created_at",datetime.now(timezone.utc))
            try:parsed=model.model_validate(data).model_dump()
            except ValueError as exc:raise ValueError(f"{kind} {id}: {exc}") from exc
            parsed["id"]=id
            merged[id]=parsed
            status="new" if id not in old else "unchanged" if flatten(parsed)==flatten(old[id]) else "changed"
            changes.append({"type":kind,"id":id,"name":parsed.get("name",id),"status":status})
        if mode=="replace":
            changes.extend({"type":kind,"id":id,"name":d.get("name",id),"status":"deleted"} for id,d in old.items() if id not in merged)
        candidate[kind]=list(merged.values())
    validate_graph(candidate)
    return candidate,changes


def validate_graph(state):
    connections={c["id"]:c for c in state["connection"]}
    points={p["id"]:p for p in state["measurement"]}
    flows={f["id"]:f for f in state["flow"]}
    for p in points.values():
        if p["connection_id"] not in connections:raise ValueError(f"{p['name']}: Verbindung fehlt.")
        protocol=connections[p["connection_id"]]["protocol"]
        if protocol!="modbus" and (not p["address"] or "+" in p["address"] or "#" in p["address"]):raise ValueError(f"{p['name']}: konkrete Adresse/Topic fehlt.")
    owners=set();grids=[]
    for f in flows.values():
        seen={f["id"]};parent=f.get("parent_id")
        while parent:
            if parent in seen:raise ValueError(f"{f['name']}: Kreis in der Knotenzuordnung.")
            if parent not in flows or flows[parent]["kind"]!="node":raise ValueError(f"{f['name']}: übergeordneter Knoten fehlt.")
            seen.add(parent);parent=flows[parent].get("parent_id")
        for value in f["datapoints"].values():
            if value and value.startswith("point:") and value[6:] not in points:raise ValueError(f"{f['name']}: Messpunkt {value} fehlt.")
        if f["kind"]=="storage" and not f.get("capacity_kwh"):raise ValueError(f"{f['name']}: Speicherkapazität fehlt.")
        if f["kind"]=="node" and f["electrical_side"]!="ac":raise ValueError("Abschnittszähler müssen AC verwenden.")
        if f["kind"]=="grid" and f["enabled"]:
            if not any(f["datapoints"].get(k) for k in ("power_total","power_l1","power_l2","power_l3")):raise ValueError("Netzleistungs-Messpunkt fehlt.")
            grids.append(f)
        if f["pv_type"]=="hybrid" and f["category"]=="pv" and not f["storage_ids"]:raise ValueError("Hybrid-WR benötigt Speicher.")
        if f["kind"]=="device" and f["category"]=="pv" and f["pv_type"]=="mppt":
            if not f["datapoints"].get("power_total") or f["run_power_w"] is not None or f["datapoints"].get("run"):raise ValueError("DC-MPPT benötigt DC-Leistung und keine RUN-Schätzung.")
        if f["kind"]=="device" and f["category"]=="pv" and f["pv_type"]=="hybrid":
            if f["electrical_side"]!="ac" or f["run_power_w"] is not None:raise ValueError("Hybrid-WR benötigt gemessene AC-Leistung.")
            if not (f["datapoints"].get("power_total") or f["power_phase_mode"]=="three" and all(f["datapoints"].get("power_"+p) for p in ("l1","l2","l3"))):raise ValueError("Hybrid-AC-Leistung fehlt.")
            if f["hybrid_ac_mode"]=="terminals" and not f["datapoints"].get("ac_input"):raise ValueError("AC-In-Messpunkt fehlt.")
        if (f["storage_ids"] or f["mppt_ids"]) and not (f["kind"]=="device" and f["category"]=="pv" and f["pv_type"]=="hybrid"):
            raise ValueError("Speicher-/MPPT-Zuordnung gehört zu einem Hybrid-WR.")
        for field,kind in (("storage_ids","storage"),("mppt_ids","device")):
            for id in f[field]:
                if id not in flows or flows[id]["kind"]!=kind or kind=="device" and flows[id]["pv_type"]!="mppt":raise ValueError("Ungültige Hybrid-Zuordnung.")
                if kind=="storage" and flows[id]["electrical_side"]!="dc":raise ValueError("Hybrid-WR darf nur DC-Speicher zuordnen.")
                if (field,id) in owners:raise ValueError("Doppelte Hybrid-Zuordnung.")
                owners.add((field,id))
    if any(f["enabled"] for f in flows.values()) and not grids:raise ValueError("Mindestens ein aktiver Netzanschluss erforderlich.")
    if len(grids)>2 or len(grids)>1 and (any(g["grid_mode"]=="signed" for g in grids) or len({g["direction"] for g in grids})!=len(grids)):
        raise ValueError("Widersprüchliche Netzanschlüsse.")
    if len(state["settings"])>1 or any(s["id"]!="app" for s in state["settings"]):raise ValueError("Nur eine Systemkonfiguration mit ID app zulässig.")


class ImportRequest(BaseModel):
    csv_text: str = Field(max_length=2_000_000)
    mode: str = "merge"
    expected_revision: str = ""


@router.get("/config/csv")
@locked
async def export_csv(template: bool=False, scope: str="all"):
    scopes={"all":list(MODELS),"measurements":["measurement"],"connections":["connection"],"flows":["flow"]}
    if scope not in scopes:raise HTTPException(422,"Ungültiger CSV-Bereich.")
    selected=scopes[scope]
    state={kind:[] for kind in MODELS} if template else await snapshot()
    state={kind:docs if kind in selected else [] for kind,docs in state.items()}
    return Response("\ufeff"+render_csv(state,selected),media_type="text/csv; charset=utf-8",headers={"Content-Disposition":'attachment; filename="energieboard-konfiguration.csv"'})


async def plan(body):
    if body.mode not in ("merge","replace"):raise HTTPException(422,"Modus merge oder replace erforderlich.")
    state=await snapshot()
    try:candidate,changes=prepare(state,body.csv_text,body.mode)
    except (ValueError,TypeError,KeyError,IndexError) as exc:raise HTTPException(422,str(exc)) from exc
    return state,candidate,changes


@router.post("/config/csv/preview")
@locked
async def preview_csv(body:ImportRequest):
    state,_,changes=await plan(body)
    return {"revision":revision(state),"changes":changes}


@router.post("/config/csv/apply")
@locked
async def apply_csv(body:ImportRequest):
    state,candidate,changes=await plan(body)
    if not body.expected_revision or body.expected_revision!=revision(state):raise HTTPException(409,"Konfiguration wurde geändert. Vorschau erneut laden.")
    backup_id=str(uuid.uuid4())
    await db.config_backups.insert_one({"id":backup_id,"created_at":datetime.now(timezone.utc),"documents":state})
    async def write(configuration):
        for kind,collection in COLLECTIONS.items():
            await db[collection].delete_many({})
            if configuration[kind]:await db[collection].insert_many(configuration[kind])
    try:await write(candidate)
    except Exception as exc:
        try:await write(state)
        except Exception:raise HTTPException(503,f"Import/Wiederherstellung fehlgeschlagen. Sicherung: {backup_id}") from exc
        raise HTTPException(503,"Import fehlgeschlagen; vorherige Konfiguration wiederhergestellt.") from exc
    from lib.recorder import request_recheck
    request_recheck()
    return {"ok":True,"backup_id":backup_id,"changes":changes}
