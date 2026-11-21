import type {LiveReport} from "@/lib/types";
import {fmtW,fmtPct} from "@/lib/format";

export default function HybridOverview({data}:{data:LiveReport}){
 if(!data.hybrids?.length)return null;
 return <section className="space-y-3"><h2 className="text-lg font-bold">Hybrid-Wechselrichter</h2><div className="grid gap-4 xl:grid-cols-2">{data.hybrids.map(h=><article key={h.id} data-testid={`hybrid-${h.id}`} className="space-y-3 rounded-xl border border-border bg-card p-4">
  <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-bold">{h.name}</h3><span className="rounded border border-border px-2 py-1 text-xs">{{inverting:"DC → AC",charging:"AC → DC",idle:"Kleine Leistung / DC-Betrieb",inconsistent:"Messwerte prüfen",unavailable:"Messbilanz fehlt"}[h.mode]??h.mode}</span></div>
  <div><p className="text-sm text-muted-foreground">WR-Wirkungsgrad {h.dc_source==="balance"?"· Schätzung aus DC-Bilanz":h.dc_source==="measured"?"· aus AC-/DC-Messung":""}</p><p className="font-mono text-2xl font-bold" data-testid={`hybrid-efficiency-${h.id}`}>{fmtPct(h.efficiency_pct)}</p></div>
  <dl className="grid grid-cols-2 gap-3 text-sm">{Object.entries({"AC netto":h.ac_net_w,"DC am WR (netto)":h.dc_net_w,"MPPTs DC":h.dc_pv_w,"DC-Lasten":h.dc_load_w,"Batterie laden":h.battery_charge_w,"Batterie entladen":h.battery_discharge_w,"WR-Verlustleistung":h.loss_w}).map(([label,value])=><div key={label}><dt className="text-xs text-muted-foreground">{label}</dt><dd className="font-mono">{fmtW(value)}</dd></div>)}</dl>
  {h.ac_output_w!=null&&<p className="text-xs text-muted-foreground">AC-Out {fmtW(h.ac_output_w)} − AC-In {fmtW(h.ac_input_w)} = Nettoleistung des Wandlers. Durchleitung zählt nicht als Erzeugung.</p>}
  {h.note&&<p className="text-xs text-amber-200">{h.note}</p>}
 </article>)}</div></section>;
}
