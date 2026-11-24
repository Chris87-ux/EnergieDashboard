import { t } from "@/lib/i18n";
import CsvConfiguration from "@/components/CsvConfiguration";
import { useState, useId, cloneElement, isValidElement } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiGet, apiPut, apiDelete, ApiError } from "@/lib/api";
import type { Connection, Measurement } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const newId = () => typeof crypto.randomUUID === "function" ? crypto.randomUUID() : Array.from(crypto.getRandomValues(new Uint8Array(16)), n=>n.toString(16).padStart(2,"0")).join("");
const newConnection = (): Connection => ({id:newId(), name:"", protocol:"mqtt", host:"", port:1883, enabled:true, username:"", password:"", tls:false, timeout_s:5, api_preset:"custom",api_path:"/{address}",api_json_path:"",api_response_format:"value",api_auth:"none",api_token_header:"Authorization",token:""});
const newPoint = (connection_id:string): Measurement => ({id:newId(), name:"", connection_id, enabled:true, record:true, unit:"W", address:"", json_path:"", scale:1, offset:0, stale_s:120, unit_id:1, register:0, function:3, datatype:"uint16", byte_order:"big", word_order:"big", history_key:""});
const selectClass = "w-full rounded-md border border-border bg-background p-2 text-sm";
function Field({name, children}:{name:string; children:React.ReactNode}) { const id=useId(); return <div className="grid gap-1 text-sm"><label htmlFor={id} className="text-muted-foreground">{name}</label>{isValidElement(children)?cloneElement(children as React.ReactElement<{id?:string}>,{id}):children}</div>; }
type Preview = {states:Record<string,{value:number|null; raw:number|null; received_at:number|null; retained:boolean; available:boolean}>; errors:string[]};

export default function Acquisition() {
  const qc = useQueryClient();
  const connections = useQuery({queryKey:["connections"],queryFn:()=>apiGet<Connection[]>("/connections")});
  const presets=useQuery({queryKey:["api-presets"],queryFn:()=>apiGet<Record<string,Partial<Connection>>>("/api-presets")});
  const points = useQuery({queryKey:["measurements"],queryFn:()=>apiGet<Measurement[]>("/measurements")});
  const preview = useQuery({queryKey:["measurement-preview"],queryFn:()=>apiGet<Preview>("/measurements/live"),refetchInterval:5000});
  const [connection, setConnection] = useState<Connection|null>(null);
  const [point, setPoint] = useState<Measurement|null>(null);
  const [search,setSearch] = useState("");
  const [busy,setBusy] = useState(false);
  const [original,setOriginal]=useState("");
  function maySwitch(){return !connection&&!point || JSON.stringify(connection??point)===original || window.confirm(t("Ungespeicherte Änderungen verwerfen?"));}
  function editConnection(c:Connection){if(connection?.id===c.id)return;if(!maySwitch())return;setPoint(null);setConnection(c);setOriginal(JSON.stringify(c));}
  function editPoint(p:Measurement){if(point?.id===p.id)return;if(!maySwitch())return;setConnection(null);setPoint(p);setOriginal(JSON.stringify(p));}

  const conn = (connections.data ?? []).find(c=>c.id===point?.connection_id);
  async function perform(action:()=>Promise<unknown>) {
    setBusy(true);
    const scroll=window.scrollY;
    try { await action(); await qc.invalidateQueries(); toast.success(t("Gespeichert")); return true; }
    catch(e) { toast.error(e instanceof ApiError ? JSON.stringify(e.body) : String(e)); return false; }
    finally { setBusy(false); requestAnimationFrame(()=>window.scrollTo({top:scroll})); }
  }
  const connectionForm = connection && <form className="grid gap-3 rounded-xl border border-border bg-card p-5 sm:grid-cols-2" onSubmit={async e=>{e.preventDefault();await perform(async()=>{const result=await apiPut(`/connections/${connection.id}`,connection);setConnection(null);return result;});}}>
      <h2 className="font-bold sm:col-span-2">{t("Verbindung bearbeiten")}</h2>
      <Field name="Name"><Input required value={connection.name} onChange={e=>setConnection({...connection,name:e.target.value})}/></Field>
      <Field name={t("Protokoll")}><select className={selectClass} value={connection.protocol} onChange={e=>{const protocol=e.target.value as Connection["protocol"];setConnection({...connection,protocol,port:protocol==="mqtt"?1883:protocol==="modbus"?502:presets.data?.[connection.api_preset]?.port??80});}}><option value="api">API / HTTP</option><option value="mqtt">MQTT</option><option value="modbus">Modbus TCP</option></select></Field>
      {connection.protocol==="api"&&<>
        <Field name={t("API-Vorlage")}><select className={selectClass} data-testid="api-preset" disabled={!presets.data} value={connection.api_preset} onChange={e=>{const api_preset=e.target.value as Connection["api_preset"];setConnection({...connection,...presets.data?.[api_preset],api_preset});}}><option value="custom">{t("Allgemeine API")}</option><option value="iobroker">ioBroker simple-api</option><option value="homeassistant">Home Assistant</option><option value="evcc">evcc</option></select></Field>
        <Field name={t("API-Aufruf (GET)")}><Input required data-testid="api-path" value={connection.api_path} onChange={e=>setConnection({...connection,api_path:e.target.value})}/></Field>
        <Field name={t("Antwortbasis / JSON-Pfad")}><Input data-testid="api-response-path" value={connection.api_json_path} onChange={e=>setConnection({...connection,api_json_path:e.target.value})}/></Field>
        <Field name={t("Antwortformat")}><select className={selectClass} value={connection.api_response_format} onChange={e=>setConnection({...connection,api_response_format:e.target.value as Connection["api_response_format"]})}><option value="value">{t("Einzelwert / JSON")}</option><option value="iobroker_bulk">{t("ioBroker-Sammelantwort (id / val)")}</option></select></Field>
        <Field name={t("API-Anmeldung")}><select data-testid="api-auth" className={selectClass} value={connection.api_auth} onChange={e=>setConnection({...connection,api_auth:e.target.value as Connection["api_auth"]})}><option value="none">{t("Keine")}</option><option value="bearer">{t("Bearer-Token")}</option><option value="basic">{t("Benutzer / Passwort (Basic)")}</option><option value="header">{t("Token in eigenem Header")}</option></select></Field>
        <p className="text-xs text-muted-foreground sm:col-span-2">{t("Aufruf relativ ab /; ")}{'{address}'} {t(" wird durch die URL-kodierte Messpunktadresse ersetzt, ")}{'{addresses}'} {t(" ist eine ioBroker-Sammelabfrage. Vorlage setzt Port, Pfad und Auswertung vor; alles bleibt editierbar. Nur lesende API-Endpunkte wählen. Es werden HTTP-GET-Anfragen ausgeführt, keine Shellbefehle.")}</p>
      </>}
      <Field name="Host / IP"><Input required value={connection.host} onChange={e=>setConnection({...connection,host:e.target.value})}/></Field>
      <Field name="Port"><Input type="number" min="1" max="65535" required value={connection.port} onChange={e=>setConnection({...connection,port:Number(e.target.value)})}/></Field>
      {(connection.protocol==="mqtt" || connection.protocol==="api" && connection.api_auth==="basic") && <><Field name={t("Benutzername")}><Input value={connection.username} onChange={e=>setConnection({...connection,username:e.target.value})}/></Field><Field name={t("Passwort (leer = beibehalten)")}><Input type="password" autoComplete="new-password" value={connection.password} onChange={e=>setConnection({...connection,password:e.target.value})}/></Field></>}
      {connection.protocol==="api"&&["bearer","header"].includes(connection.api_auth)&&<>
        <Field name={t("API-Token (leer = beibehalten)")}><Input type="password" data-testid="api-token" autoComplete="new-password" placeholder={connection.token_set?t("Token gespeichert"):""} value={connection.token} onChange={e=>setConnection({...connection,token:e.target.value,clear_token:false})}/></Field>
        {connection.api_auth==="header"&&<Field name={t("Token-Header")}><Input value={connection.api_token_header} onChange={e=>setConnection({...connection,api_token_header:e.target.value})}/></Field>}
        <label><input type="checkbox" checked={connection.clear_token??false} onChange={e=>setConnection({...connection,clear_token:e.target.checked,token:""})}/> {t(" Gespeicherten Token löschen")}</label>
      </>}
      {connection.protocol!=="modbus" && <label><input type="checkbox" checked={connection.tls} onChange={e=>setConnection({...connection,tls:e.target.checked})}/> TLS / HTTPS</label>}
      <label><input type="checkbox" checked={connection.enabled} onChange={e=>setConnection({...connection,enabled:e.target.checked})}/> {t(" Aktiv")}</label>
      <div className="flex gap-2 sm:col-span-2"><Button type="submit" disabled={busy}>{t("Speichern")}</Button><Button type="button" variant="outline" onClick={()=>{if(maySwitch())setConnection(null);}}>{t("Abbrechen")}</Button></div>
    </form>;
  const pointForm = point && <form className="grid gap-3 rounded-xl border border-border bg-card p-5 sm:grid-cols-2" onSubmit={async e=>{e.preventDefault();await perform(async()=>{const result=await apiPut(`/measurements/${point.id}`,point);setPoint(null);return result;});}}>
      <h2 className="font-bold sm:col-span-2">{t("Messpunkt bearbeiten")}</h2>
      <Field name="Name"><Input required value={point.name} onChange={e=>setPoint({...point,name:e.target.value})}/></Field>
      <Field name={t("Verbindung")}><select className={selectClass} value={point.connection_id} onChange={e=>setPoint({...point,connection_id:e.target.value})}>{connections.data?.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></Field>
      {conn?.protocol!=="modbus" ? <><Field name={conn?.protocol==="mqtt"?t("MQTT-Topic (exakt)"):conn?.api_preset==="evcc"?t("evcc-Wertpfad (z. B. grid.power)"):conn?.api_preset==="homeassistant"?t("Entity-ID (z. B. sensor.netzleistung)"):t("Adresse / Variable {address}")}><Input required={conn?.protocol==="mqtt" || conn?.api_preset==="evcc" || (conn?.api_path??"").includes("{address")} value={point.address} onChange={e=>setPoint({...point,address:e.target.value})}/></Field>{(conn?.protocol==="mqtt" || conn?.protocol==="api") && <Field name={t("JSON-Pfad (optional, unter Antwortbasis)")}><Input value={point.json_path} onChange={e=>setPoint({...point,json_path:e.target.value})}/></Field>}</> : <>
        <Field name={t("Unit-ID")}><Input type="number" min="0" max="247" value={point.unit_id} onChange={e=>setPoint({...point,unit_id:Number(e.target.value)})}/></Field>
        <Field name={t("Registeradresse (0-basiert)")}><Input type="number" min="0" max="65535" value={point.register} onChange={e=>setPoint({...point,register:Number(e.target.value)})}/></Field>
        <Field name={t("Funktion")}><select className={selectClass} value={point.function} onChange={e=>setPoint({...point,function:Number(e.target.value) as 3|4})}><option value="3">03 Holding Register</option><option value="4">04 Input Register</option></select></Field>
        <Field name={t("Datentyp")}><select className={selectClass} value={point.datatype} onChange={e=>setPoint({...point,datatype:e.target.value})}>{["uint16","int16","uint32","int32","float32","float64"].map(t=><option key={t}>{t}</option>)}</select></Field>
        {(["byte_order","word_order"] as const).map(key=><Field key={key} name={key==="byte_order"?t("Byte-Reihenfolge"):t("Wort-Reihenfolge")}><select className={selectClass} value={point[key]} onChange={e=>setPoint({...point,[key]:e.target.value})}><option>big</option><option>little</option></select></Field>)}
      </>}
      <Field name={t("Einheit nach Umrechnung")}><select className={selectClass} value={point.unit} onChange={e=>setPoint({...point,unit:e.target.value})}>{["W","kW","Wh","kWh","%","Hz","V","A","bool","°C","h","L/h","L","m³/h","m³","kg/h","kg",""].map(u=><option key={u}>{u}</option>)}</select></Field>
      {(["scale","offset","stale_s"] as const).filter(key=>key!=="stale_s"||conn?.protocol==="mqtt").map(key=><Field key={key} name={{scale:t("Faktor"),offset:"Offset",stale_s:t("MQTT-Gültigkeit (Sekunden)")}[key]}><Input type="number" step="any" value={point[key]} onChange={e=>setPoint({...point,[key]:Number(e.target.value)})}/></Field>)}
      <label><input type="checkbox" checked={point.enabled} onChange={e=>setPoint({...point,enabled:e.target.checked})}/> {t(" Aktiv")}</label>
      <label><input type="checkbox" checked={point.record} onChange={e=>setPoint({...point,record:e.target.checked})}/> {t(" Rohwert aufzeichnen")}</label>
      <p className="break-all text-xs text-muted-foreground sm:col-span-2">{t("Stabile ID: point:")}{point.id}{t(". Wert = Rohwert × Faktor + Offset. Geräte-Einheit passend wählen.")}</p>
      <div className="flex gap-2 sm:col-span-2"><Button type="submit" disabled={busy}>{t("Speichern")}</Button><Button type="button" variant="outline" onClick={()=>{if(maySwitch())setPoint(null);}}>{t("Abbrechen")}</Button></div>
    </form>;
  return <>
    <h1 className="text-2xl font-bold">{t("Datenerfassung")}</h1>
    <CsvConfiguration />
    <p className="text-muted-foreground">{t("Verbindungen und Messpunkte einmal anlegen. Geräte verwenden anschließend die stabile Messpunkt-ID. Alle Adapter lesen ausschließlich Werte.")}</p>
    {[connections.error, points.error, preview.error].some(Boolean) && <p role="alert">{t("Datenerfassung nicht erreichbar. Verbindung zum Server prüfen.")}</p>}
    <div className="flex flex-wrap gap-2"><Button disabled={busy} onClick={()=>editConnection(newConnection())}>{t("Verbindung hinzufügen")}</Button><Button disabled={busy||!connections.data?.length} onClick={()=>editPoint(newPoint(connections.data![0].id))}>{t("Messpunkt hinzufügen")}</Button></div>
    {connection && !(connections.data??[]).some(c=>c.id===connection.id) && connectionForm}

    <section className="grid gap-2"><h2 className="text-lg font-bold">{t("Verbindungen")}</h2>{connections.data?.map(c=><div key={c.id} className="space-y-2"><div data-testid={`connection-row-${c.id}`} className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card p-3"><b className="min-w-0 break-all">{c.name}</b><span className="break-all">{c.protocol==="api"?`API (${c.api_preset})`:c.protocol} · {c.host}:{c.port} · {c.enabled?t("aktiv"):t("inaktiv")}</span><Button variant="outline" onClick={()=>editConnection({...c,password:"",token:"",clear_token:false})}>{t("Bearbeiten")}</Button><Button variant="ghost" onClick={()=>{if(window.confirm(t("Verbindung „{0}“ löschen?", c.name)))void perform(()=>apiDelete(`/connections/${c.id}`));}}>{t("Löschen")}</Button></div>{connection?.id===c.id&&connectionForm}</div>)}</section>
    {point && !(points.data??[]).some(p=>p.id===point.id) && pointForm}

    <section className="space-y-3"><h2 className="text-lg font-bold">{t("Messpunkte und Diagnose")}</h2><Input placeholder={t("Messpunkte suchen")} aria-label={t("Messpunkte suchen")} value={search} onChange={e=>setSearch(e.target.value)}/>
      {preview.data?.errors.map(e=><p role="alert" key={e} className="text-red-300">{e}</p>)}
      {points.data?.filter(p=>(p.name+p.id).toLowerCase().includes(search.toLowerCase())).map(p=>{const s=preview.data?.states[p.id];return <div key={p.id} className="space-y-2"><div data-testid={`measurement-row-${p.id}`} className="grid gap-2 rounded-lg border border-border bg-card p-3 sm:grid-cols-[1fr_auto]">
        <div className="min-w-0"><b className="break-all">{p.name}</b><p>{s?.available?`${s.value} ${p.unit}`:t("Nicht verfügbar / veraltet")} {t(" · Rohwert ")}{s?.raw??"–"}{s?.retained?t(" · gespeicherte MQTT-Nachricht"):""}</p><p className="break-all text-xs text-muted-foreground">point:{p.id}</p><p className="text-xs text-muted-foreground">{t("Letzter Empfang: ")}{s?.received_at?new Date(s.received_at*1000).toLocaleString():"–"}</p></div>
        <div className="flex gap-2"><Button variant="outline" onClick={()=>editPoint(p)}>{t("Bearbeiten")}</Button><Button variant="ghost" onClick={()=>{if(window.confirm(t("Messpunkt „{0}“ löschen?", p.name)))void perform(()=>apiDelete(`/measurements/${p.id}`));}}>{t("Löschen")}</Button></div>
      </div>{point?.id===p.id&&pointForm}</div>;})}
    </section>
  </>;
}
