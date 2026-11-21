import {ArrowDownLeft, ArrowUpRight, UtilityPole} from "lucide-react";
import {fmtW} from "@/lib/format";
import type {LiveReport} from "@/lib/types";

export default function GridConnection({data}:{data:LiveReport|undefined}) {
 const summary=data?.grid_configured?data.summary:null;
 const available=summary?.grid_import_w!=null&&summary?.grid_export_w!=null;
 return <section className="mx-auto w-full max-w-xl rounded-xl border border-primary bg-card p-4 panel-shadow" data-testid="grid-connection" aria-label="Netzanschluss">
  <div className="flex items-center justify-between gap-3"><h2 className="flex items-center gap-2 font-bold"><UtilityPole className="size-5 text-primary"/>Netzanschluss</h2><span className="text-xs text-muted-foreground">{!data?"Warte auf Messwerte":!data.grid_configured?"Bitte einrichten":available?"Aktuell":"Messwerte unvollständig"}</span></div>
  <div className="mt-3 grid grid-cols-2 gap-3">
   <div data-testid="kpi-grid-import"><p className="flex items-center gap-1 text-xs text-muted-foreground"><ArrowDownLeft className="size-4 text-red-400"/>Bezug</p><p className="mt-1 font-mono text-xl font-bold sm:text-2xl" data-testid="kpi-grid-import-value">{fmtW(summary?.grid_import_w)}</p></div>
   <div data-testid="kpi-grid-export"><p className="flex items-center gap-1 text-xs text-muted-foreground"><ArrowUpRight className="size-4 text-emerald-400"/>Lieferung / Einspeisung</p><p className="mt-1 font-mono text-xl font-bold sm:text-2xl" data-testid="kpi-grid-export-value">{fmtW(summary?.grid_export_w)}</p></div>
  </div>
 </section>;
}
