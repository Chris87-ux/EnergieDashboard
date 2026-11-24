import {useState} from "react";
import {useQuery,useQueryClient} from "@tanstack/react-query";
import {apiGet,apiPost} from "@/lib/api";
import {useFlows,useSettings} from "@/lib/queries";
import {t,locale} from "@/lib/i18n";
import {fmtKwh,fmtDuration} from "@/lib/format";
import {Button} from "@/components/ui/button";
import {toast} from "sonner";
interface State {id:string;name:string;profile:string;status:number;count:number;today:number;month:number;runtime_s:number|null;runtime_alarm:boolean;had_gap:boolean;last_valid:number|null;}
interface Event {id:string;started_at:number;ended_at:number;outcome:string;energy_kwh:number|null;energy_complete:boolean;}
const states=[t("Aus"),t("Bereit"),t("Läuft"),t("Pause"),t("Fertig"),t("Unbekannt"),t("Startet")];
const outcomes:Record<string,string>={completed:t("Abgeschlossen"),aborted:t("Abgebrochen"),interrupted:t("Messlücke"),unobserved:t("Start unbeobachtet"),reconfigured:t("Neu konfiguriert")};
function History({id,timezone}:{id:string;timezone:string}){
 const [open,setOpen]=useState(false);const query=useQuery({queryKey:["cycle-events",id],queryFn:()=>apiGet<Event[]>(`/cycles/${id}/events`),enabled:open,refetchInterval:open?30000:false});
 const date=new Intl.DateTimeFormat(locale,{timeZone:timezone,dateStyle:"short",timeStyle:"short"});
 return <details className="mt-3 text-xs" onToggle={e=>setOpen(e.currentTarget.open)}><summary className="cursor-pointer">{t("Letzte Läufe")}</summary><div className="overflow-auto"><table className="mt-2 w-full text-left"><thead><tr><th>{t("Ende")}</th><th>{t("Status")}</th><th>{t("Dauer")}</th><th>kWh</th></tr></thead><tbody>{query.data?.map(event=><tr key={event.id}><td className="p-1">{date.format(new Date(event.ended_at*1000))}</td><td className="p-1">{outcomes[event.outcome]??event.outcome}</td><td className="p-1">{fmtDuration(Math.max(0,event.ended_at-event.started_at))}</td><td className="p-1">{fmtKwh(event.energy_kwh)}{event.energy_kwh!=null&&!event.energy_complete?" *":""}</td></tr>)}</tbody></table></div>{query.isError&&<p role="alert">{t("Verlauf konnte nicht geladen werden.")}</p>}<p className="mt-1 text-muted-foreground">{t("* Energiehistorie unvollständig. Unterbrochene und unbeobachtete Läufe erhöhen den Zähler nicht.")}</p></details>;
}
export default function CycleOverview({full=false}:{full?:boolean}){
 const qc=useQueryClient();const config=useFlows();const settings=useSettings();const enabled=config.data?.some(f=>f.kind==="device"&&f.cycle_tracking?.enabled);
 const query=useQuery({queryKey:["cycle-status"],queryFn:()=>apiGet<State[]>("/cycles/status"),enabled:!!enabled,refetchInterval:10000});
 if(!full&&!enabled)return null;
 return <section className="space-y-3" data-testid="cycle-overview"><h2 className="text-lg font-bold">{t("Gerätestatus und Läufe")}</h2><p className="text-xs text-muted-foreground">{t("Gezählt werden bestätigte abgeschlossene Läufe seit Aktivierung der Erkennung. Profile und Schwellen sind im Geräteeditor einstellbar.")}</p>
 {!enabled&&<p className="text-sm text-muted-foreground">{t("Noch keine Zykluserkennung aktiv. Im Geräteeditor den Reiter Gerätezyklen öffnen.")}</p>}
 {query.isError&&<p role="alert">{t("Gerätestatus konnte nicht geladen werden.")}</p>}
 <div className="grid gap-3 lg:grid-cols-2">{query.data?.map(state=><article key={state.id} className="min-w-0 space-y-2 rounded-xl border border-border bg-card p-4" data-testid={"cycle-device-"+state.id}><div className="flex flex-wrap justify-between gap-2"><h3 className="break-all font-bold">{state.name}</h3><b className={state.status===4?"text-emerald-400":state.status===5?"text-amber-300":"text-primary"}>{states[state.status]??t("Unbekannt")}</b></div><div className="flex flex-wrap gap-4 text-sm"><span>{t("Heute")}: <b>{state.today}</b></span><span>{t("Dieser Monat")}: <b>{state.month}</b></span><span>{t("Gesamt")}: <b>{state.count}</b></span>{state.runtime_s!=null&&<span>{t("Laufzeit")}: {fmtDuration(state.runtime_s)}</span>}</div>{state.runtime_alarm&&<p role="alert" className="text-sm text-amber-300">{t("Die konfigurierte maximale Laufzeit ist überschritten.")}</p>}{state.had_gap&&<p className="text-xs text-amber-300">{t("Zwischenzeitlich fehlten Messwerte; der Erkennungsverlauf ist eingeschränkt.")}</p>}{state.status===4&&<Button variant="outline" onClick={async()=>{try{await apiPost(`/cycles/${state.id}/ack`,{});await qc.invalidateQueries({queryKey:["cycle-status"]});}catch(error){toast.error(String(error));}}}>{t("Fertig bestätigen")}</Button>}<History id={state.id} timezone={settings.data?.timezone??"Europe/Berlin"}/></article>)}</div>
 </section>;
}
