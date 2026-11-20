import { fmtKwh, fmtPct, fmtW } from "@/lib/format";
import type { LiveReport, LiveStorage } from "@/lib/types";

function Storage({storage:s, aggregate=false}:{storage:LiveStorage;aggregate?:boolean}) {
  const power=s.charge_w==null||s.discharge_w==null?null:s.charge_w-s.discharge_w;
  const runtime=s.runtime_h==null?"–":s.runtime_h>=48?`${(s.runtime_h/24).toFixed(1)} Tage`:`${Math.floor(s.runtime_h)} h ${Math.round((s.runtime_h%1)*60)} min`;
  return <article data-testid={`storage-${s.id}`} className={`space-y-3 rounded-xl border bg-card p-4 ${aggregate?"border-primary sm:col-span-2":"border-border"}`}>
    <div className="flex flex-wrap justify-between gap-2"><h3 className="font-bold">{s.name}</h3><span>{fmtPct(s.soc_pct)} · {fmtKwh(s.capacity_kwh)}</span></div>
    {s.hybrid_name && <p className="text-xs text-muted-foreground">Hybrid-WR: {s.hybrid_name}</p>}
    <div role="meter" aria-label={`${s.name} SOC`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={s.soc_pct??undefined} className="h-5 overflow-hidden rounded bg-muted"><div className="h-full bg-primary transition-all" style={{width:`${s.soc_pct??0}%`}}/></div>
    <div className="flex justify-between text-xs text-muted-foreground"><span>Entladen {fmtW(s.discharge_w)}</span><span>Laden {fmtW(s.charge_w)}</span></div>
    <div className="relative h-5 overflow-hidden rounded bg-muted" aria-label={`${s.name} Lade-/Entladeleistung`}><div className="absolute bottom-0 left-1/2 top-0 w-px bg-foreground"/><div className="absolute h-full transition-all" style={{background:power!=null&&power<0?"#F59E0B":"var(--primary)",width:`${Math.min(50,Math.abs(power??0)/s.max_power_w*50)}%`,left:power!=null&&power<0?undefined:"50%",right:power!=null&&power<0?"50%":undefined}}/></div>
    <dl className="grid grid-cols-2 gap-2 text-sm"><div><dt className="text-muted-foreground">Restenergie</dt><dd>{fmtKwh(s.remaining_kwh)}</dd></div><div><dt className="text-muted-foreground">Bis Reserve nutzbar</dt><dd>{fmtKwh(s.usable_kwh)}</dd></div><div><dt className="text-muted-foreground">Restlaufzeit, geglättet</dt><dd>{runtime}</dd></div><div><dt className="text-muted-foreground">Leistung, geglättet</dt><dd>{fmtW(s.smoothed_power_w)}</dd></div></dl>
    {(s.soc_pct==null||s.capacity_kwh==null||power==null)&&<p className="text-xs text-amber-300">Unvollständige Daten: SOC, Kapazität oder Leistung prüfen.</p>}
  </article>;
}
export default function StorageOverview({data}:{data:LiveReport}) {
  if(!data.storages.length&&!data.dc_values.length)return null;
  return <section className="space-y-3"><h2 className="text-lg font-bold">Speicher und DC-Anlage</h2><p className="text-xs text-muted-foreground">Separate Messwerte. Restlaufzeit bis SOC-Reserve aus einem 5-Minuten-Mittel; bei Laden oder geringer Entladung ohne Zeitangabe. Rechnerische Energie ohne Verlustmodell.</p>
    <div className="grid gap-3 sm:grid-cols-2">{data.storage_total&&<Storage storage={data.storage_total} aggregate/>}{data.storages.map(s=><div key={s.id}><Storage storage={s}/><p className="mt-1 text-xs text-muted-foreground">Knoten: {data.nodes.find(n=>n.id===s.parent_id)?.name??"Hauptebene"}</p></div>)}</div>
    <div className="grid gap-3 sm:grid-cols-3">{data.dc_values.map(v=><div key={v.id} className="rounded-lg border border-border bg-card p-3"><b>{v.name}</b><p>{fmtW(v.power_w)} DC</p>{v.hybrid_name&&<p className="text-xs text-muted-foreground">{v.hybrid_name}</p>}</div>)}</div>
  </section>;
}
