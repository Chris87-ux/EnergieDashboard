import { useState } from "react";
import FlowCard from "@/components/FlowCard";
import { Input } from "@/components/ui/input";
import { fmtW } from "@/lib/format";
import type { FlowEnergy, LiveReport } from "@/lib/types";

export default function NodeOverview({data,energy,showInactive=false}:{data:LiveReport;energy:FlowEnergy[];showInactive?:boolean}) {
 const [search,setSearch]=useState("");
 const energyById=new Map(energy.map(e=>[e.flow_id,e]));
 const match=(name:string)=>name.toLowerCase().includes(search.toLowerCase());
 function group(id:string|null,depth=0):React.ReactNode {
  if(depth>50)return null;
  const node=data.nodes.find(n=>n.id===id);
  const children=data.nodes.filter(n=>n.parent_id===id);
  const flows=data.flows.filter(f=>f.parent_id===id&&!f.storage_id);
  const shown=flows.filter(f=>(!search||match(f.name)||match(node?.name??""))&&(showInactive||!f.hidden));
  return <section key={id??"root"} className={`node-section space-y-3 border-l-4 border-primary bg-card p-3 sm:p-4 ${depth?"ml-1 sm:ml-3":""}`} data-testid={`node-group-${id??"root"}`}>
   <div className="flex flex-wrap justify-between gap-3"><h3 className="font-bold">{node?`▣ ${node.name}`:"Hauptebene"}</h3>{node&&<span className="text-sm">Zähler netto {fmtW(node.meter_w)} · Rest {fmtW(node.difference_w)}</span>}</div>
   {node&&<details className="text-xs text-muted-foreground"><summary>Phasen und Verrechnung</summary><p>Verbrauch positiv · Erzeugung negativ · Kinder netto {fmtW(node.children_w)}</p>{Object.entries(node.phases).map(([p,v])=><p key={p}>{p}: {fmtW(v)}</p>)}<p>DC-Speicher und MPPTs werden separat angezeigt.</p></details>}
   <details open={depth===0||!!search}><summary className="cursor-pointer text-sm text-primary">Geräte und Unterknoten ({flows.length+children.length})</summary>
    <div className="mt-3 grid gap-3 xl:grid-cols-2">{(["in","out"] as const).map(direction=><div key={direction} className="space-y-2"><h4 className="text-sm text-muted-foreground">{direction==="in"?"Erzeugung / Zufluss":"Verbrauch / Abfluss"}</h4>{shown.filter(f=>f.direction===direction).map(f=><FlowCard key={f.flow_id} flow={f} energy={energyById.get(f.flow_id)}/>)}</div>)}</div>
    <div className="mt-3 space-y-3">{children.map(n=>group(n.id,depth+1))}</div>
   </details>
  </section>;
 }
 return <section className="space-y-3"><h2 className="text-lg font-bold">Produktion und Verbrauch</h2><Input aria-label="Geräte suchen" placeholder="Geräte oder Knoten suchen" value={search} onChange={e=>setSearch(e.target.value)}/>{group(null)}</section>;
}
