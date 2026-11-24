import {useState} from "react";
import {locale,t} from "@/lib/i18n";
import type {ChartData} from "@/lib/chartTypes";

const normalNumber=new Intl.NumberFormat(locale,{maximumFractionDigits:2});
const smallNumber=new Intl.NumberFormat(locale,{maximumSignificantDigits:3});
const number={format:(v:number)=>(v!==0&&Math.abs(v)<0.01?smallNumber:normalNumber).format(v)};
const unitLabel=(unit:string)=>unit==="cycles"?t("Zyklen"):unit==="status"?t("Status"):unit||"—";
const statusLabel=(value:number)=>[t("Aus"),t("Bereit"),t("Läuft"),t("Pause"),t("Fertig"),t("Unbekannt"),t("Startet")][Math.round(value)]??number.format(value);
export default function TimeChart({data,timezone}:{data:ChartData;timezone:string}){
 const [selected,setSelected]=useState<number|null>(null);const [hidden,setHidden]=useState<string[]>([]);
 const lines=data.series.filter(s=>!hidden.includes(s.kind+":"+s.reference_id));
 const units=[...new Set(lines.map(s=>s.unit))];const panels=units.length?Array.from({length:Math.ceil(units.length/2)},(_,i)=>units.slice(i*2,i*2+2)):[[]];
 const dates=new Intl.DateTimeFormat(locale,{timeZone:timezone,day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"});
 const length=Math.max(1,...data.series.map(s=>s.points.length));const at=selected==null?null:Math.min(selected,length-1);
 const scales=new Map(units.map(unit=>{const values=lines.filter(s=>s.unit===unit).flatMap(s=>s.points.flatMap(p=>p[1]==null?[]:[p[1]]));const low=Math.min(0,...values),high=Math.max(0,...values);return [unit,[low,high===low?low+1:high]] as const;}));
 const bounds=(unit:string)=>scales.get(unit)??[0,1];
 return <div className="min-w-0 space-y-3" data-testid="time-chart">
 <div className="flex flex-wrap gap-2">{data.series.map(s=>{const key=s.kind+":"+s.reference_id;return <button type="button" key={key} className="flex max-w-full items-center gap-2 break-all rounded border border-border px-2 py-1 text-xs" aria-pressed={!hidden.includes(key)} onClick={()=>setHidden(hidden.includes(key)?hidden.filter(k=>k!==key):[...hidden,key])}><span className="size-2 shrink-0 rounded" style={{background:s.color}}/>{s.name} · {unitLabel(s.unit)}{hidden.includes(key)?" ×":""}</button>;})}</div>
 {panels.map((panel,pi)=>{const active=lines.filter(s=>panel.includes(s.unit));const width=960,left=80,right=880,top=26,bottom=232;const x=(i:number)=>left+(right-left)*i/Math.max(1,length-1);const y=(v:number,unit:string)=>{const [a,b]=bounds(unit);return bottom-(v-a)/(b-a)*(bottom-top);};return <div key={pi} className="overflow-x-auto rounded border border-border"><svg role="img" aria-label={data.name} viewBox="0 0 960 280" className="w-full min-w-[560px]" onMouseMove={e=>{const box=e.currentTarget.getBoundingClientRect();setSelected(Math.max(0,Math.min(length-1,Math.round(((e.clientX-box.left)*width/box.width-left)/(right-left)*(length-1)))));}}>
 <title>{data.name}</title>
 {[0,.25,.5,.75,1].map(f=><g key={f}><line x1={left} x2={right} y1={top+(bottom-top)*f} y2={top+(bottom-top)*f} stroke="currentColor" opacity=".12"/>{panel.map((unit,index)=>{const [a,b]=bounds(unit);return <text key={unit} x={index?right+8:left-8} y={top+(bottom-top)*f+4} textAnchor={index?"start":"end"} fill="currentColor" fontSize="11">{number.format(b-(b-a)*f)}</text>;})}</g>)}
 {panel.map((unit,index)=><text key={unit} x={index?right:left} y={16} textAnchor={index?"end":"start"} fill="currentColor" fontSize="12">{unitLabel(unit)}</text>)}
 {active.map(s=>{let path="",drawing=false;for(let i=0;i<s.points.length;i++){const value=s.points[i][1];if(value==null){drawing=false;continue;}path+=(drawing?(s.digital?`H${x(i)}V${y(value,s.unit)}`:`L${x(i)},${y(value,s.unit)}`):`M${x(i)},${y(value,s.unit)}l0,0`);drawing=true;}return <path key={s.kind+s.reference_id} d={path} fill="none" stroke={s.color} strokeWidth="2" strokeLinecap="round"/>;})}
 {[0,.25,.5,.75,1].map(f=>{const i=Math.min(length-1,Math.round((length-1)*f)),stamp=data.series[0]?.points[i]?.[0];return stamp&&<text key={f} x={x(i)} y={256} textAnchor={f===0?"start":f===1?"end":"middle"} fill="currentColor" fontSize="11">{dates.format(new Date(stamp))}</text>;})}
 {at!=null&&<line x1={x(at)} x2={x(at)} y1={top} y2={bottom} stroke="currentColor" strokeDasharray="4 4" opacity=".5"/>}
 </svg></div>;})}
 <label className="grid gap-1 text-xs text-muted-foreground">{t("Zeitpunkt im Chart")}<input type="range" min={0} max={length-1} value={at??0} onChange={e=>setSelected(Number(e.target.value))} aria-label={t("Zeitpunkt im Chart")}/></label>
 {at!=null&&<div className="flex flex-wrap gap-x-5 gap-y-1 rounded bg-muted p-2 text-xs"><b>{data.series[0]?.points[at]&&dates.format(new Date(data.series[0].points[at][0]))}</b>{lines.map(s=>{const value=s.points[at]?.[1];return <span key={s.kind+s.reference_id} className="break-all">{s.name}: <b>{value==null?t("n. v."):s.unit==="status"?statusLabel(value):number.format(value)+" "+unitLabel(s.unit)}</b></span>;})}</div>}
 {!data.series.some(s=>s.points.some(p=>p[1]!=null))&&<p className="text-sm text-muted-foreground">{t("Für diesen Zeitraum sind keine aufgezeichneten Werte vorhanden.")}</p>}
 <p className="text-xs text-muted-foreground">{t("Lücken werden nicht mit Null aufgefüllt. Verschiedene Einheiten verwenden getrennte Achsen; mehr als zwei Einheiten erscheinen in weiteren Teilgrafiken.")}</p>
 </div>;
}
