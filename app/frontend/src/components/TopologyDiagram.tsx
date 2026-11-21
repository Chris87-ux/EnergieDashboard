import {useState} from "react";
import FlowDiagram from "@/components/FlowDiagram";
import {Button} from "@/components/ui/button";
import type {LiveFlow,LiveReport} from "@/lib/types";

export default function TopologyDiagram({data,showInactive}:{data:LiveReport;showInactive:boolean}){
 const [selected,setSelected]=useState<string|null>(null);const [page,setPage]=useState(0);
 const current=data.nodes.find(n=>n.id===selected);const id=current?.id??null;
 const parents:typeof data.nodes=[];let next=current;const seen=new Set<string>();
 while(next&&!seen.has(next.id)){parents.unshift(next);seen.add(next.id);next=data.nodes.find(n=>n.id===next?.parent_id);}
 const select=(id:string|null)=>{setSelected(id);setPage(0);};
 const children:LiveFlow[]=data.nodes.filter(n=>n.parent_id===id).map(n=>{
  const power=n.meter_w??n.children_w;
  return {flow_id:`node:${n.id}`,node_id:n.id,name:n.name,category:"custom",direction:power!=null&&power<0?"in":"out",icon:n.icon,color:n.color,power_w:power==null?null:Math.abs(power),available:power!=null,parent_id:id,power_phase_mode:n.phase_mode,power_phase:n.phase,phases:n.phases,frequency_hz:null,estimated:false,storage_id:null,hidden:false,zero_since:null,telemetry:{}};
 });
 const flows=[...children,...data.flows.filter(f=>f.category!=="grid"&&f.parent_id===id&&(showInactive||!f.hidden))];
 const batches:LiveFlow[][]=[[]];
 for(const flow of flows){let batch=batches[batches.length-1];if(batch.filter(f=>f.direction===flow.direction).length>=4){batch=[];batches.push(batch);}batch.push(flow);}
 const pages=batches.length;const activePage=Math.min(page,pages-1);
 const offset=batches.slice(0,activePage).reduce((sum,batch)=>sum+batch.length,0);
 return <div className="space-y-3" data-testid="topology-diagram">
  <nav aria-label="Knotenpfad" className="flex flex-wrap items-center gap-1"><Button variant="outline" size="sm" onClick={()=>select(null)}>Haus</Button>{parents.map(n=><span key={n.id}> → <Button size="sm" variant={n.id===id?"default":"outline"} onClick={()=>select(n.id)}>{n.name}</Button></span>)}</nav>
  <p className="text-xs text-muted-foreground">Rechteckige Knoten öffnen ihre Kinder. Zählerleistung ist netto; die Bilanz zählt jeden Abschnitt einmal.</p>
  <FlowDiagram flows={batches[activePage]} summary={data.ok?data.summary:null} onSelectNode={select} hubName={current?.name} hubLabel={current?"Zähler / Abschnitt netto":undefined} hubPower={current?(current.meter_w??current.children_w):undefined}/>
  {pages>1&&<div className="flex items-center justify-between gap-2 text-xs"><Button variant="outline" disabled={activePage===0} onClick={()=>setPage(activePage-1)}>Zurück</Button><span>Elemente {offset+1}–{offset+batches[activePage].length} von {flows.length}</span><Button variant="outline" disabled={activePage+1===pages} onClick={()=>setPage(activePage+1)}>Weiter</Button></div>}
 </div>;
}
