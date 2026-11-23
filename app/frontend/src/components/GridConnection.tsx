import {ArrowDownLeft, ArrowUpRight, UtilityPole} from "lucide-react";
import {fmtW, fmtHz, fmtKwh} from "@/lib/format";
import type {LiveReport, EnergyTotals} from "@/lib/types";

export default function GridConnection({data,period,periodLabel="Heute",energyOnly=false}:{data:LiveReport|undefined;period?:EnergyTotals;periodLabel?:string;energyOnly?:boolean}) {
 const summary=data?.grid_configured?data.summary:null;
 const available=summary?.grid_import_w!=null&&summary?.grid_export_w!=null;
 return <section className="mx-auto w-full max-w-xl rounded-xl border border-primary bg-card p-4 panel-shadow" data-testid="grid-connection" aria-label="Netzanschluss">
  <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="flex items-center gap-2 font-bold"><UtilityPole className="size-5 text-primary"/>Netzanschluss</h2><span className="text-xs text-muted-foreground">{energyOnly?periodLabel:!data?"Warte auf Messwerte":!data.grid_configured?"Bitte einrichten":available?"Aktuell":"Messwerte unvollständig"}</span></div>
  <p className="mt-2 text-xs text-muted-foreground" data-testid="grid-frequency">Frequenz aktuell: <span className="font-mono">{fmtHz(data?.frequency_hz)}</span></p>
  {!energyOnly&&<div className="mt-3 grid grid-cols-2 gap-3">
   <div data-testid="kpi-grid-import"><p className="flex items-center gap-1 text-xs text-muted-foreground"><ArrowDownLeft className="size-4 text-red-400"/>Bezug</p><p className="mt-1 font-mono text-xl font-bold sm:text-2xl" data-testid="kpi-grid-import-value">{fmtW(summary?.grid_import_w)}</p></div>
   <div data-testid="kpi-grid-export"><p className="flex items-center gap-1 text-xs text-muted-foreground"><ArrowUpRight className="size-4 text-emerald-400"/>Lieferung / Einspeisung</p><p className="mt-1 font-mono text-xl font-bold sm:text-2xl" data-testid="kpi-grid-export-value">{fmtW(summary?.grid_export_w)}</p></div>
  </div>}
  <div className="mt-3 grid grid-cols-2 gap-3 border-t border-border pt-3 text-sm">
   <div><p className="text-xs text-muted-foreground">{periodLabel} Bezug</p><p className="font-mono font-bold" data-testid="grid-period-import">{fmtKwh(period?.grid_import_kwh)}</p></div>
   <div><p className="text-xs text-muted-foreground">{periodLabel} geliefert</p><p className="font-mono font-bold" data-testid="grid-period-export">{fmtKwh(period?.grid_export_kwh)}</p></div>
  </div>
  {period?.incomplete&&<p className="mt-2 text-xs text-amber-300">Zeitraum enthält Messlücken; Energiewerte und Kennzahlen sind unvollständig.</p>}
 </section>;
}
