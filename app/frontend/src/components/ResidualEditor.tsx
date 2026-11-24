import {useState} from "react";
import {useQuery,useQueryClient} from "@tanstack/react-query";
import {apiGet,apiPut,ApiError} from "@/lib/api";
import {t} from "@/lib/i18n";
import type {Flow,ConsumerGroup} from "@/lib/types";
import {Dialog,DialogContent,DialogHeader,DialogTitle,DialogDescription} from "@/components/ui/dialog";
import {Input} from "@/components/ui/input";
import {Button} from "@/components/ui/button";
import {ICONS} from "@/lib/icons";
import {toast} from "sonner";

export default function ResidualEditor({flow,onClose}:{flow:Flow;onClose:()=>void}){
 const qc=useQueryClient();const [busy,setBusy]=useState(false);
 const [form,setForm]=useState(flow.residual??{name:"",group_id:null,color:null,icon:"",sort_order:null});
 const groups=useQuery({queryKey:["consumer-groups"],queryFn:()=>apiGet<ConsumerGroup[]>("/consumer-groups")});
 return <Dialog open onOpenChange={open=>{if(!open)onClose();}}><DialogContent data-testid="residual-editor"><DialogHeader><DialogTitle>{t("Automatischer Restverbraucher")}</DialogTitle><DialogDescription>{t("Der Knotenzähler und die Kinder bestimmen die Leistung. Dieses Gerät hat keine eigenen Datenpunkte und wird nicht zusätzlich zur Anlagenbilanz gezählt.")}</DialogDescription></DialogHeader><form className="space-y-3" onSubmit={async e=>{e.preventDefault();setBusy(true);try{await apiPut(`/residuals/${flow.parent_id}`,form);await qc.invalidateQueries();onClose();}catch(error){toast.error(error instanceof ApiError?JSON.stringify(error.body):String(error));}finally{setBusy(false);}}}>
 <label className="grid gap-1 text-sm">{t("Anzeigename")}<Input data-testid="residual-name" value={form.name} placeholder={flow.name} maxLength={60} onChange={e=>setForm({...form,name:e.target.value})}/></label>
 <label className="grid gap-1 text-sm">{t("Verbrauchergruppe")}<select data-testid="residual-group" className="rounded border border-border bg-background p-2" value={form.group_id??""} onChange={e=>setForm({...form,group_id:e.target.value||null})}><option value="">{t("Keine Gruppe")}</option>{groups.data?.map(g=><option key={g.id} value={g.id}>{g.name}</option>)}</select></label>
 <label className="grid gap-1 text-sm">{t("Symbol")}<select className="rounded border border-border bg-background p-2" value={form.icon} onChange={e=>setForm({...form,icon:e.target.value})}><option value="">{t("Vom Knoten übernehmen")}</option>{Object.entries(ICONS).map(([id,item])=><option key={id} value={id}>{item.label}</option>)}</select></label>
 <label className="grid gap-1 text-sm">{t("Farbe")}<Input type="color" value={form.color??flow.color} onChange={e=>setForm({...form,color:e.target.value})}/></label>
 <label className="grid gap-1 text-sm">{t("Anzeigereihenfolge")}<Input type="number" value={form.sort_order??flow.sort_order} onChange={e=>setForm({...form,sort_order:Number(e.target.value)})}/></label>
 <div className="flex gap-2"><Button type="submit" disabled={busy}>{t("Speichern")}</Button><Button type="button" variant="outline" onClick={onClose}>{t("Abbrechen")}</Button></div>
 </form></DialogContent></Dialog>;
}
