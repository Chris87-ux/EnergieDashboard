import { t } from "@/lib/i18n";
import {useState} from "react";
import {useQuery,useQueryClient} from "@tanstack/react-query";
import {apiGet,apiPut,apiDelete,ApiError} from "@/lib/api";
import type {ConsumerGroup} from "@/lib/types";
import {Button} from "@/components/ui/button";
import {Input} from "@/components/ui/input";
import {toast} from "sonner";

export default function ConsumerGroupsConfig(){
 const qc=useQueryClient();const groups=useQuery({queryKey:["consumer-groups"],queryFn:()=>apiGet<ConsumerGroup[]>("/consumer-groups")});
 const [form,setForm]=useState<ConsumerGroup|null>(null);const [busy,setBusy]=useState(false);
 async function save(){if(!form?.name.trim())return;setBusy(true);try{await apiPut(`/consumer-groups/${form.id}`,{...form,name:form.name.trim()});setForm(null);await qc.invalidateQueries();}catch(e){toast.error(e instanceof ApiError?JSON.stringify(e.body):String(e));}finally{setBusy(false);}}
 async function remove(g:ConsumerGroup){if(!confirm(t("Verbrauchergruppe „{0}“ löschen?", g.name)))return;try{await apiDelete(`/consumer-groups/${g.id}`);await qc.invalidateQueries();}catch(e){toast.error(e instanceof ApiError?JSON.stringify(e.body):String(e));}}
 return <section className="space-y-3 rounded-xl border border-border p-4" data-testid="consumer-groups-config"><div className="flex flex-wrap justify-between gap-2"><h2 className="text-lg font-bold">{t("Verbrauchergruppen")}</h2><Button type="button" onClick={()=>setForm({id:typeof crypto.randomUUID==="function"?crypto.randomUUID():Array.from(crypto.getRandomValues(new Uint8Array(16)),n=>n.toString(16).padStart(2,"0")).join(""),name:"",color:"#38BDF8",sort_order:100})}>{t("Verbrauchergruppe hinzufügen")}</Button></div><p className="text-xs text-muted-foreground">{t("Zusätzliche Auswertung über Knotengrenzen hinweg. Verbraucher im Geräteformular zuordnen; Gruppensummen zählen nicht nochmals zur Anlagenbilanz.")}</p>
 {groups.isError&&<p role="alert">{t("Verbrauchergruppen konnten nicht geladen werden.")}</p>}
 {groups.data?.map(g=><div className="flex flex-wrap items-center gap-3" key={g.id}><span className="size-3 rounded" style={{background:g.color}}/><b className="break-all">{g.name}</b><Button type="button" variant="outline" onClick={()=>setForm(g)}>{t("Gruppe bearbeiten")}</Button><Button type="button" variant="ghost" onClick={()=>remove(g)}>{t("Gruppe löschen")}</Button></div>)}
 {form&&<form className="grid gap-3 rounded-lg border border-border bg-card p-4 sm:grid-cols-3" onSubmit={e=>{e.preventDefault();void save();}}><label className="text-sm">{t("Gruppenname")}<Input data-testid="consumer-group-name" maxLength={80} required value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/></label><label className="text-sm">{t("Gruppenfarbe")}<Input type="color" value={form.color} onChange={e=>setForm({...form,color:e.target.value})}/></label><label className="text-sm">{t("Anzeigereihenfolge")}<Input type="number" value={form.sort_order} onChange={e=>setForm({...form,sort_order:Number(e.target.value)})}/></label><div className="flex gap-2"><Button type="submit" disabled={busy}>{t("Gruppe speichern")}</Button><Button type="button" variant="outline" onClick={()=>setForm(null)}>{t("Abbrechen")}</Button></div></form>}
 </section>;
}
