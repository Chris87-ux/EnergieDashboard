import { Link } from "react-router-dom";
import { ArrowRight, Gauge, Leaf, Sun } from "lucide-react";
import {useState} from "react";
import GridConnection from "@/components/GridConnection";
import TopologyDiagram from "@/components/TopologyDiagram";
import HybridOverview from "@/components/HybridOverview";
import StorageOverview from "@/components/StorageOverview";
import NodeOverview from "@/components/NodeOverview";
import MethodBadge from "@/components/MethodBadge";
import { buttonVariants } from "@/components/ui/button";
import { fmtKwh, fmtPct, fmtTime, fmtW } from "@/lib/format";
import { useEnergyToday, useLive } from "@/lib/queries";
import type { LucideIcon } from "lucide-react";

function Kpi({ label, value, icon: Icon, color, testid }: { label: string; value: string; icon: LucideIcon; color: string; testid: string }) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 panel-shadow animate-fade-up" data-testid={testid}>
      <div className="flex items-center gap-2 text-xs font-medium text-[#8EA8C3]">
        <Icon className="size-4" style={{ color }} />
        {label}
      </div>
      <div className="mt-2 font-mono text-xl font-extrabold tracking-tight sm:text-2xl" data-testid={`${testid}-value`}>
        {value}
      </div>
    </div>
  );
}

export default function Dashboard({embedded=false}:{embedded?:boolean}) {
  const live = useLive();
  const today = useEnergyToday();
  const data = live.isError ? undefined : live.data;
  const s = data?.ok ? data.summary : null;
  const [showInactive,setShowInactive]=useState(false);
  const todayReport = today.isError ? undefined : today.data;

  const visualData = data ? {...data, summary:{...data.summary, autarky_pct:todayReport?.totals.autarky_pct??null, self_consumption_pct:todayReport?.totals.self_consumption_pct??null}} : undefined;

  return (
    <>
      <section className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-[var(--primary)]">Aktuelle Leistung</p>
          <h1 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl" data-testid="dashboard-title">
            Energiefluss{data ? ` · ${data.site_name}` : ""}
          </h1>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-[#8EA8C3]">
          <span data-testid="dashboard-updated">{data ? `Aktualisiert ${fmtTime(data.ts)}` : live.isError ? "Backend nicht erreichbar" : "Lade Livedaten…"}</span>
        </div>
      </section>

      {!embedded && data && data.errors.length > 0 && (
        <div className="rounded-xl border border-[#7F1D1D] bg-[#450A0A]/60 p-3 text-sm text-[#FECACA]" data-testid="dashboard-errors">
          {data.errors.join(" · ")}
          {" "}
          <Link className="underline" to="/system">Verbindung einrichten</Link>
        </div>
      )}

      <GridConnection data={data} period={todayReport?.totals} />
      <section className="grid grid-cols-2 gap-3 md:grid-cols-4" data-testid="kpi-strip">
        <Kpi label={s?.production_estimated ? "Produktion · geschätzt" : "Produktion"} value={fmtW(s?.production_w)} icon={Sun} color="#EAB308" testid="kpi-production" />
        <Kpi label="Verbrauch" value={fmtW(s?.consumption_w)} icon={Gauge} color="#38BDF8" testid="kpi-consumption" />
        <Kpi label="Autarkiegrad · Heute" value={fmtPct(todayReport?.totals.autarky_pct)} icon={Leaf} color="#34D399" testid="kpi-autarky" />
        <Kpi label="Eigenverbrauch · Heute" value={fmtPct(todayReport?.totals.self_consumption_pct)} icon={Sun} color="#FBBF24" testid="kpi-self-consumption" />
      </section>

      {s && s.notes.length>0 && <details className="text-xs text-muted-foreground"><summary>Bilanzhinweise</summary>{s.notes.map(n=><p key={n}>{n}</p>)}<p>Produktion kombiniert die jeweils gemessenen AC-/DC-Erzeugungsgrenzen. Autarkie und Eigenverbrauch beziehen sich auf den aufgezeichneten heutigen Zeitraum.</p></details>}
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={showInactive} onChange={e=>setShowInactive(e.target.checked)}/>Inaktive anzeigen{data ? ` (${data.flows.filter(f=>f.hidden&&f.category!=="grid").length} ausgeblendet)` : ""}</label>
      <section className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
        <div className="flow-visual lg:col-span-8">
          {visualData && <TopologyDiagram data={visualData} showInactive={showInactive} />}
        </div>
        <aside className="today-aside space-y-4 lg:col-span-4">
          <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 panel-shadow" data-testid="today-panel">
            <div className="flex items-center justify-between">
              <h2 className="font-heading text-lg font-semibold">Heute</h2>
              <Link to="/energie" className={buttonVariants({ variant: "ghost", size: "sm" })} data-testid="today-panel-open-energy">
                Bilanz <ArrowRight className="size-4" />
              </Link>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-3">
              <div className="rounded-lg bg-muted p-3">
                <div className="text-xs text-[#8EA8C3]">Produktion</div>
                <div className="font-mono text-lg font-bold" data-testid="today-in-kwh">{fmtKwh(todayReport?.totals.in_kwh)}</div>
              </div>
              <div className="rounded-lg bg-muted p-3">
                <div className="text-xs text-[#8EA8C3]">Verbrauch</div>
                <div className="font-mono text-lg font-bold" data-testid="today-out-kwh">{fmtKwh(todayReport?.totals.out_kwh)}</div>
              </div>
            </div>
            <details className="mt-4" open={(todayReport?.flows.length ?? 0) <= 12}>
              <summary className="cursor-pointer text-xs text-muted-foreground">Tageswerte der Geräte</summary>
            <ul className="mt-3 space-y-2">
              {(todayReport?.flows.filter(f=>!f.storage_id&&f.electrical_side!=="dc") ?? []).map((f) => (
                <li key={f.flow_id} className="flex items-center justify-between gap-2 text-sm" data-testid={`today-row-${f.flow_id}`}>
                  <span className="flex min-w-0 items-center gap-2">
                    <span className="size-2 shrink-0 rounded-full" style={{ background: f.color }} />
                    <span className="truncate">{f.name}</span>
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    <MethodBadge method={f.total.method} />
                    <span className="w-24 text-right font-mono text-xs font-semibold">{fmtKwh(f.total.kwh)}</span>
                  </span>
                </li>
              ))}
              {today.isLoading && <li className="text-sm text-[#8EA8C3]">Berechne Tageswerte…</li>}
              {today.isError && <li className="text-sm text-[#8EA8C3]">Tageswerte derzeit nicht verfügbar</li>}
            </ul>
            </details>
          </div>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 panel-shadow text-sm">
            <div className="text-xs text-[#8EA8C3]">Nicht zugeordneter Verbrauch (Netzbilanz − Geräte)</div>
            <div className="mt-1 font-mono text-xl font-bold" data-testid="house-rest-power">{fmtW(s?.house_rest_w)}</div>
            <p className="mt-1 text-xs text-[#8EA8C3]">Nicht separat gemessener Restverbrauch bzw. Messabweichung.</p>
          </div>
        </aside>
      </section>

      {data && !data.grid_configured && <p role="alert" className="rounded-lg border border-amber-500 p-4">Ein Netzanschluss ist erforderlich. Unter Konfiguration einen Netzanschluss anlegen und Messpunkte zuordnen.</p>}

      {data && <NodeOverview showInactive={showInactive} data={data} energy={todayReport?.flows.filter(f=>!f.storage_id&&f.electrical_side!=="dc") ?? []} />}
      {data && <HybridOverview data={data} />}
      {data && <StorageOverview data={data} />}
    </>
  );
}
