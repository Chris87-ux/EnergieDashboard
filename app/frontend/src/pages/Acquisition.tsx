import CsvConfiguration from "@/components/CsvConfiguration";
import { useState, useId, cloneElement, isValidElement } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiGet, apiPut, apiDelete, ApiError } from "@/lib/api";
import type { Connection, Measurement } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const newId = () => typeof crypto.randomUUID === "function" ? crypto.randomUUID() : Array.from(crypto.getRandomValues(new Uint8Array(16)), n=>n.toString(16).padStart(2,"0")).join("");
const newConnection = (): Connection => ({id:newId(), name:"", protocol:"mqtt", host:"", port:1883, enabled:true, username:"", password:"", tls:false, timeout_s:5});
const newPoint = (connection_id:string): Measurement => ({id:newId(), name:"", connection_id, enabled:true, record:true, unit:"W", address:"", json_path:"", scale:1, offset:0, stale_s:120, unit_id:1, register:0, function:3, datatype:"uint16", byte_order:"big", word_order:"big", history_key:""});
const selectClass = "w-full rounded-md border border-border bg-background p-2 text-sm";
function Field({name, children}:{name:string; children:React.ReactNode}) { const id=useId(); return <div className="grid gap-1 text-sm"><label htmlFor={id} className="text-muted-foreground">{name}</label>{isValidElement(children)?cloneElement(children as React.ReactElement<{id?:string}>,{id}):children}</div>; }
type Preview = {states:Record<string,{value:number|null; raw:number|null; received_at:number|null; retained:boolean; available:boolean}>; errors:string[]};

export default function Acquisition() {
  const qc = useQueryClient();
  const connections = useQuery({queryKey:["connections"],queryFn:()=>apiGet<Connection[]>("/connections")});
  const points = useQuery({queryKey:["measurements"],queryFn:()=>apiGet<Measurement[]>("/measurements")});
  const preview = useQuery({queryKey:["measurement-preview"],queryFn:()=>apiGet<Preview>("/measurements/live"),refetchInterval:5000});
  const [connection, setConnection] = useState<Connection|null>(null);
  const [point, setPoint] = useState<Measurement|null>(null);
  const [search,setSearch] = useState("");
  const [busy,setBusy] = useState(false);
  const [original,setOriginal]=useState("");
  function maySwitch(){return !connection&&!point || JSON.stringify(connection??point)===original || window.confirm("Ungespeicherte Änderungen verwerfen?");}
  function editConnection(c:Connection){if(connection?.id===c.id)return;if(!maySwitch())return;setPoint(null);setConnection(c);setOriginal(JSON.stringify(c));}
  function editPoint(p:Measurement){if(point?.id===p.id)return;if(!maySwitch())return;setConnection(null);setPoint(p);setOriginal(JSON.stringify(p));}

  const conn = (connections.data ?? []).find(c=>c.id===point?.connection_id);
  async function perform(action:()=>Promise<unknown>) {
    setBusy(true);
    const scroll=window.scrollY;
    try { await action(); await qc.invalidateQueries(); toast.success("Gespeichert"); return true; }
    catch(e) { toast.error(e instanceof ApiError ? JSON.stringify(e.body) : String(e)); return false; }
    finally { setBusy(false); requestAnimationFrame(()=>window.scrollTo({top:scroll})); }
  }
  const connectionForm = connection && <form className="grid gap-3 rounded-xl border border-border bg-card p-5 sm:grid-cols-2" onSubmit={async e=>{e.preventDefault();if(await perform(()=>apiPut(`/connections/${connection.id}`,connection)))setConnection(null);}}>
      <h2 className="font-bold sm:col-span-2">Verbindung bearbeiten</h2>
      <Field name="Name"><Input required value={connection.name} onChange={e=>setConnection({...connection,name:e.target.value})}/></Field>
      <Field name="Protokoll"><select className={selectClass} value={connection.protocol} onChange={e=>{const protocol=e.target.value as Connection["protocol"];setConnection({...connection,protocol,port:protocol==="mqtt"?1883:protocol==="modbus"?502:8087});}}>{["mqtt","modbus","iobroker"].map(p=><option key={p}>{p}</option>)}</select></Field>
      <Field name="Host / IP"><Input required value={connection.host} onChange={e=>setConnection({...connection,host:e.target.value})}/></Field>
      <Field name="Port"><Input type="number" min="1" max="65535" required value={connection.port} onChange={e=>setConnection({...connection,port:Number(e.target.value)})}/></Field>
      {connection.protocol==="mqtt" && <><Field name="Benutzername"><Input value={connection.username} onChange={e=>setConnection({...connection,username:e.target.value})}/></Field><Field name="Passwort (leer = beibehalten)"><Input type="password" autoComplete="new-password" value={connection.password} onChange={e=>setConnection({...connection,password:e.target.value})}/></Field></>}
      {connection.protocol!=="modbus" && <label><input type="checkbox" checked={connection.tls} onChange={e=>setConnection({...connection,tls:e.target.checked})}/> TLS / HTTPS</label>}
      <label><input type="checkbox" checked={connection.enabled} onChange={e=>setConnection({...connection,enabled:e.target.checked})}/> Aktiv</label>
      <div className="flex gap-2 sm:col-span-2"><Button type="submit" disabled={busy}>Speichern</Button><Button type="button" variant="outline" onClick={()=>{if(maySwitch())setConnection(null);}}>Abbrechen</Button></div>
    </form>;
  const pointForm = point && <form className="grid gap-3 rounded-xl border border-border bg-card p-5 sm:grid-cols-2" onSubmit={async e=>{e.preventDefault();if(await perform(()=>apiPut(`/measurements/${point.id}`,point)))setPoint(null);}}>
      <h2 className="font-bold sm:col-span-2">Messpunkt bearbeiten</h2>
      <Field name="Name"><Input required value={point.name} onChange={e=>setPoint({...point,name:e.target.value})}/></Field>
      <Field name="Verbindung"><select className={selectClass} value={point.connection_id} onChange={e=>setPoint({...point,connection_id:e.target.value})}>{connections.data?.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
      {conn?.protocol!=="modbus" ? <><Field name={conn?.protocol==="mqtt"?"MQTT-Topic (exakt)":"ioBroker-Datenpunkt-ID"}><Input required value={point.address} onChange={e=>setPoint({...point,address:e.target.value})}/></Field>{conn?.protocol==="mqtt" && <Field name="JSON-Pfad (optional, z. B. data.power)"><Input value={point.json_path} onChange={e=>setPoint({...point,json_path:e.target.value})}/></Field>}</> : <>
        <Field name="Unit-ID"><Input type="number" min="0" max="247" value={point.unit_id} onChange={e=>setPoint({...point,unit_id:Number(e.target.value)})}/></Field>
        <Field name="Registeradresse (0-basiert)"><Input type="number" min="0" max="65535" value={point.register} onChange={e=>setPoint({...point,register:Number(e.target.value)})}/></Field>
        <Field name="Funktion"><select className={selectClass} value={point.function} onChange={e=>setPoint({...point,function:Number(e.target.value) as 3|4})}><option value="3">03 Holding Register</option><option value="4">04 Input Register</option></select></Field>
        <Field name="Datentyp"><select className={selectClass} value={point.datatype} onChange={e=>setPoint({...point,datatype:e.target.value})}>{["uint16","int16","uint32","int32","float32","float64"].map(t=><option key={t}>{t}</option>)}</select></Field>
        {(["byte_order","word_order"] as const).map(key=><Field key={key} name={key==="byte_order"?"Byte-Reihenfolge":"Wort-Reihenfolge"}><select className={selectClass} value={point[key]} onChange={e=>setPoint({...point,[key]:e.target.value})}><option>big</option><option>little</option></select></Field>)}
      </>}
      <Field name="Einheit nach Umrechnung"><select className={selectClass} value={point.unit} onChange={e=>setPoint({...point,unit:e.target.value})}>{["W","kW","Wh","kWh","%","Hz","V","A","bool","°C","h","L/h","L","m³/h","m³","kg/h","kg",""].map(u=><option key={u}>{u}</option>)}</select></Field>
      {(["scale","offset","stale_s"] as const).map(key=><Field key={key} name={{scale:"Faktor",offset:"Offset",stale_s:"MQTT-Gültigkeit (Sekunden)"}[key]}><Input type="number" step="any" value={point[key]} onChange={e=>setPoint({...point,[key]:Number(e.target.value)})}/></Field>)}
      <label><input type="checkbox" checked={point.enabled} onChange={e=>setPoint({...point,enabled:e.target.checked})}/> Aktiv</label>
      <label><input type="checkbox" checked={point.record} onChange={e=>setPoint({...point,record:e.target.checked})}/> Rohwert aufzeichnen</label>
      <p className="break-all text-xs text-muted-foreground sm:col-span-2">Stabile ID: point:{point.id}. Wert = Rohwert × Faktor + Offset. Geräte-Einheit passend wählen.</p>
      <div className="flex gap-2 sm:col-span-2"><Button type="submit" disabled={busy}>Speichern</Button><Button type="button" variant="outline" onClick={()=>{if(maySwitch())setPoint(null);}}>Abbrechen</Button></div>
    </form>;
  return <>
    <h1 className="text-2xl font-bold">Datenerfassung</h1>
    <CsvConfiguration />
    <p className="text-muted-foreground">Verbindungen und Messpunkte einmal anlegen. Geräte verwenden anschließend die stabile Messpunkt-ID. Alle Adapter lesen ausschließlich Werte.</p>
    {[connections.error, points.error, preview.error].some(Boolean) && <p role="alert">Datenerfassung nicht erreichbar. Verbindung zum Server prüfen.</p>}
    <div className="flex flex-wrap gap-2"><Button onClick={()=>editConnection(newConnection())}>Verbindung hinzufügen</Button><Button disabled={!connections.data?.length} onClick={()=>editPoint(newPoint(connections.data![0].id))}>Messpunkt hinzufügen</Button></div>
    {connection && !(connections.data??[]).some(c=>c.id===connection.id) && connectionForm}

    <section className="grid gap-2"><h2 className="text-lg font-bold">Verbindungen</h2>{connections.data?.map(c=><div key={c.id} className="space-y-2"><div data-testid={`connection-row-${c.id}`} className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card p-3"><b className="min-w-0 break-all">{c.name}</b><span className="break-all">{c.protocol} · {c.host}:{c.port} · {c.enabled?"aktiv":"inaktiv"}</span><Button variant="outline" onClick={()=>editConnection({...c,password:""})}>Bearbeiten</Button><Button variant="ghost" onClick={()=>{if(window.confirm(`Verbindung „${c.name}“ löschen?`))void perform(()=>apiDelete(`/connections/${c.id}`));}}>Löschen</Button></div>{connection?.id===c.id&&connectionForm}</div>)}</section>
    {point && !(points.data??[]).some(p=>p.id===point.id) && pointForm}

    <section className="space-y-3"><h2 className="text-lg font-bold">Messpunkte und Diagnose</h2><Input placeholder="Messpunkte suchen" aria-label="Messpunkte suchen" value={search} onChange={e=>setSearch(e.target.value)}/>
      {preview.data?.errors.map(e=><p role="alert" key={e} className="text-red-300">{e}</p>)}
      {points.data?.filter(p=>(p.name+p.id).toLowerCase().includes(search.toLowerCase())).map(p=>{const s=preview.data?.states[p.id];return <div key={p.id} className="space-y-2"><div data-testid={`measurement-row-${p.id}`} className="grid gap-2 rounded-lg border border-border bg-card p-3 sm:grid-cols-[1fr_auto]">
        <div className="min-w-0"><b className="break-all">{p.name}</b><p>{s?.available?`${s.value} ${p.unit}`:"Nicht verfügbar / veraltet"} · Rohwert {s?.raw??"–"}{s?.retained?" · gespeicherte MQTT-Nachricht":""}</p><p className="break-all text-xs text-muted-foreground">point:{p.id}</p><p className="text-xs text-muted-foreground">Letzter Empfang: {s?.received_at?new Date(s.received_at*1000).toLocaleString():"–"}</p></div>
        <div className="flex gap-2"><Button variant="outline" onClick={()=>editPoint(p)}>Bearbeiten</Button><Button variant="ghost" onClick={()=>{if(window.confirm(`Messpunkt „${p.name}“ löschen?`))void perform(()=>apiDelete(`/measurements/${p.id}`));}}>Löschen</Button></div>
      </div>{point?.id===p.id&&pointForm}</div>;})}
    </section>
  </>;
}
