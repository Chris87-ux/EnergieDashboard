import { ArrowDownLeft, ArrowUpRight } from "lucide-react";
import MethodBadge from "@/components/MethodBadge";
import { CATEGORY_LABELS, fmtHz, fmtKwh, fmtW } from "@/lib/format";
import { iconFor } from "@/lib/icons";
import { PHASES, type FlowEnergy, type LiveFlow } from "@/lib/types";

interface Props {
  flow: LiveFlow;
  energy?: FlowEnergy;
}

export default function FlowCard({ flow, energy }: Props) {
  const Icon = iconFor(flow.icon);
  const max = Math.max(1, ...PHASES.map((p) => Math.abs(flow.phases[p] ?? 0)));
  const totalOnly = flow.available && PHASES.every(p => flow.phases[p] == null);
  const modeLabel = totalOnly ? "Gesamtwert · ohne Phasenaufteilung" : flow.power_phase_mode === "three" ? "3-phasig" : `1-phasig · ${flow.power_phase}`;
  return (
    <div
      data-testid={`flow-card-${flow.flow_id}`}
      className="group relative overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 panel-shadow transition-[transform,border-color] duration-200 ease-out hover:-translate-y-0.5 hover:border-[var(--primary)]/60 animate-fade-up"
    >
      <span className="absolute inset-y-0 left-0 w-1" style={{ background: flow.color }} />
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-lg" style={{ background: `${flow.color}22` }}>
            <Icon className="size-5" style={{ color: flow.color }} />
          </span>
          <div>
            <div className="font-heading text-base font-semibold leading-tight">{flow.name}</div>
            <div className="text-xs text-[#8EA8C3]">
              {CATEGORY_LABELS[flow.category]} · {modeLabel}
              {flow.estimated && " · RUN-Schätzung"}
            </div>
          </div>
        </div>
        <span
          className="flex items-center gap-1 rounded-md border border-[var(--border)] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-[#8EA8C3]"
          data-testid={`flow-card-direction-${flow.flow_id}`}
        >
          {flow.direction === "in" ? <ArrowDownLeft className="size-3" /> : <ArrowUpRight className="size-3" />}
          {flow.direction === "in" ? "Produktion" : "Verbrauch"}
        </span>
      </div>
      <div className="mt-3 flex items-end justify-between">
        <div
          className={`font-mono text-2xl font-extrabold tracking-tight ${flow.available ? "" : "text-[#F87171]"}`}
          data-testid={`flow-card-power-${flow.flow_id}`}
        >
          {fmtW(flow.power_w)}
        </div>
        {flow.frequency_hz !== null && (
          <div className="font-mono text-xs text-[#93C5FD]" data-testid={`flow-card-frequency-${flow.flow_id}`}>
            {fmtHz(flow.frequency_hz)}
          </div>
        )}
      </div>
      {flow.category === "generator" && <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
        {Object.entries({engine_temperature:["Motortemperatur","°C"],efficiency:["Effizienz","%"],fuel_consumption:["Kraftstoffverbrauch",String(flow.telemetry?.fuel_unit??"L/h")],operating_hours:["Betriebsstunden","h"]}).map(([key,[label,unit]])=><div key={key}><dt className="text-muted-foreground">{label}</dt><dd>{flow.telemetry?.[key]==null?"n. v.":`${flow.telemetry[key]} ${unit}`}</dd></div>)}
      </dl>}
      {!totalOnly && <div className="mt-3 space-y-1.5">
        {PHASES.map((p) => {
          const v = flow.phases[p];
          const used = flow.power_phase_mode === "three" || p === flow.power_phase;
          return (
            <div key={p} className="flex items-center gap-2 text-xs" data-testid={`flow-card-phase-${flow.flow_id}-${p}`}>
              <span className="w-5 font-mono font-semibold text-[#93C5FD]">{p}</span>
              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-[var(--background)]">
                {used && v !== null && (
                  <div
                    className="h-full rounded-full transition-[width] duration-500"
                    style={{ width: `${Math.min(100, (Math.abs(v) / max) * 100)}%`, background: flow.color }}
                  />
                )}
              </div>
              <span className="w-20 text-right font-mono text-[#F0F4F8]">{used ? fmtW(v) : "—"}{flow.estimated_phases?.includes(p) ? " (ber.)" : ""}</span>
            </div>
          );
        })}
      </div>}
      {energy && (
        <div className="mt-3 flex items-center justify-between border-t border-[var(--border)] pt-3 text-xs">
          <span className="text-[#8EA8C3]">Heute</span>
          <span className="flex items-center gap-2">
            <MethodBadge method={energy.total.method} />
            <span className="font-mono font-semibold" data-testid={`flow-card-today-${flow.flow_id}`}>
              {fmtKwh(energy.total.kwh)}
            </span>
          </span>
        </div>
      )}
    </div>
  );
}
