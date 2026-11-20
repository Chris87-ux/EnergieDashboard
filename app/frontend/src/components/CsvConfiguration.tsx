import {useState} from "react";
import {useQueryClient} from "@tanstack/react-query";
import {apiPost, ApiError} from "@/lib/api";
import {Button} from "@/components/ui/button";
import {toast} from "sonner";

type Preview={revision:string;changes:{type:string;id:string;name:string;status:string}[]};
export default function CsvConfiguration(){
 const qc=useQueryClient();const [text,setText]=useState("");const [mode,setMode]=useState("merge");
 const [preview,setPreview]=useState<Preview|null>(null);const [busy,setBusy]=useState(false);const [error,setError]=useState("");const [confirmed,setConfirmed]=useState(false);
 async function run(apply=false){setBusy(true);setError("");try{
  if(apply){const r=await apiPost<{backup_id:string}>("/config/csv/apply",{csv_text:text,mode,expected_revision:preview?.revision});await qc.invalidateQueries();setPreview(null);toast.success(`CSV übernommen. Sicherung: ${r.backup_id}`);}
  else setPreview(await apiPost<Preview>("/config/csv/preview",{csv_text:text,mode}));
 }catch(e){setError(e instanceof ApiError?JSON.stringify((e.body as {detail?:unknown})?.detail??e.body):String(e));if(apply)setPreview(null);}finally{setBusy(false);}}
 return <details className="space-y-3 rounded-xl border border-border bg-card p-4" data-testid="csv-configuration"><summary className="cursor-pointer font-bold">Konfiguration als CSV herunterladen / hochladen</summary>
  <p className="text-sm text-muted-foreground">UTF-8, Semikolon-getrennt. Enthält Verbindungen, Messpunkte, Geräte, Knoten, Speicher und Darstellung. Zugangsdaten bleiben ausgespart; vorhandene Kennwörter bleiben beim Import erhalten. Stabile IDs nicht ändern.</p>
  <div className="flex flex-wrap gap-3"><a href="/api/config/csv" download className="text-primary underline">Gesamtkonfiguration CSV</a><a href="/api/config/csv?scope=measurements" download className="text-primary underline">Messpunkte CSV</a><a href="/api/config/csv?scope=connections" download className="text-primary underline">Verbindungen CSV</a><a href="/api/config/csv?template=true&scope=measurements" download className="text-primary underline">Messpunkt-Vorlage</a></div>
  <label className="grid gap-1 text-sm">CSV-Datei<input type="file" accept=".csv,text/csv" onChange={async e=>{setPreview(null);setError("");const file=e.target.files?.[0];if(!file)return;if(file.size>2_000_000){setError("Maximal 2 MB zulässig.");return;}setText(await file.text());}} /></label>
  <label className="grid gap-1 text-sm">Importmodus<select className="rounded border border-border bg-background p-2" value={mode} onChange={e=>{setMode(e.target.value);setPreview(null);setConfirmed(false);}}><option value="merge">Ergänzen / anhand der ID aktualisieren</option><option value="replace">Gesamte Konfiguration ersetzen</option></select></label>
  {mode==="replace"&&<label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>Nicht enthaltene Einträge sollen entfernt werden.</label>}
  <Button disabled={!text||busy} onClick={()=>void run()}>Importvorschau prüfen</Button>
  {error&&<p role="alert" className="break-words text-sm text-red-300">{error}</p>}
  {preview&&<div className="space-y-3"><p className="text-sm">Vor der Übernahme wird die aktuelle Konfiguration gesichert. Die Messhistorie bleibt erhalten.</p><div className="max-h-72 overflow-auto"><table className="w-full text-left text-xs"><thead><tr><th>Typ</th><th>Name</th><th>Änderung</th></tr></thead><tbody>{preview.changes.map(c=><tr key={c.type+c.id}><td className="p-1">{c.type}</td><td className="max-w-48 break-all p-1">{c.name}</td><td className="p-1">{{new:"Neu",changed:"Geändert",unchanged:"Unverändert",deleted:"Entfernt"}[c.status]??c.status}</td></tr>)}</tbody></table></div><Button disabled={busy||mode==="replace"&&!confirmed} onClick={()=>void run(true)}>Geprüften Import übernehmen</Button></div>}
 </details>;
}
