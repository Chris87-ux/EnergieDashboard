import { useState } from "react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import { useSettings } from "@/lib/queries";
import { apiPut } from "@/lib/api";
import type { Appearance as Settings } from "@/lib/types";
import { Button } from "@/components/ui/button";

export const defaultAppearance:Settings={layout:"rounded",background:"#0B132B",surface:"#111D42",accent:"#38BDF8"};
export default function Appearance() {
  const settings=useSettings();const qc=useQueryClient();
  const [draft,setDraft]=useState<Settings|null>(null);const [busy,setBusy]=useState(false);
  const form=draft??settings.data?.appearance??defaultAppearance;
  const set=(patch:Partial<Settings>)=>setDraft({...form,...patch});
  return <><h1 className="text-2xl font-bold">Darstellung</h1><p className="text-muted-foreground">Darstellung und Farben werden zentral gespeichert und auch für die eingebettete Ansicht verwendet.</p>
    <div className="grid gap-4 md:grid-cols-3">{(["square","rounded","flow"] as const).map(layout=><button key={layout} type="button" aria-pressed={form.layout===layout} onClick={()=>set({layout})} className={`space-y-3 border p-5 text-left ${form.layout===layout?"border-primary":"border-border"}`} style={{background:form.background,borderRadius:layout==="square"?0:18}}><b>{layout==="square"?"Kompakt / eckig":layout==="rounded"?"Modern / Karten":"Flussdiagramm"}</b><div className="flex gap-2">{["Netz","Haus","PV"].map(label=><div key={label} className="flex-1 p-3 text-center text-xs" style={{background:form.surface,borderRadius:layout==="flow"?40:layout==="square"?0:10,border:`1px solid ${form.accent}`,color:form.accent}}>{label}</div>)}</div></button>)}</div>
    <div className="flex flex-wrap gap-5">{(["background","surface","accent"] as const).map(key=><label key={key} className="grid gap-2">{{background:"Hintergrund",surface:"Flächen",accent:"Akzentfarbe"}[key]}<input type="color" value={form[key]} onChange={e=>set({[key]:e.target.value})}/></label>)}</div>
    <div className="flex flex-wrap gap-2">{[{name:"Nachtblau",background:"#0B132B",surface:"#111D42",accent:"#38BDF8"},{name:"Graphit",background:"#101216",surface:"#20242B",accent:"#34D399"},{name:"Aubergine",background:"#1B1225",surface:"#30203F",accent:"#D8B4FE"}].map(({name,...colors})=><Button key={name} variant="outline" onClick={()=>set(colors)}>{name}</Button>)}</div>
    <Button disabled={!settings.data||busy} onClick={async()=>{setBusy(true);try{await apiPut("/settings",{...settings.data,appearance:form});await qc.invalidateQueries({queryKey:["settings"]});setDraft(null);toast.success("Darstellung gespeichert");}catch{toast.error("Speichern fehlgeschlagen");}finally{setBusy(false);}}}>Darstellung speichern</Button>
    <div className="rounded-lg border border-border bg-card p-4"><h2 className="font-bold">Flow-Ansicht einbetten</h2><a className="break-all text-primary underline" href="/flow" target="_blank" rel="noreferrer">{window.location.origin}/flow</a><pre className="mt-3 overflow-auto text-xs">{`<iframe src="${window.location.origin}/flow" title="Energiefluss" width="100%" height="900" style="border:0"></iframe>`}</pre><p className="mt-2 text-xs text-muted-foreground">Bei einer HTTPS-Zielseite auch Energieboard über HTTPS bereitstellen. Die Ansicht enthält keine Navigation und keine Konfigurationsformulare.</p></div>
  </>;
}
