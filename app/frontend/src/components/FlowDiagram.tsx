import { useEffect, useState } from "react";
import { House } from "lucide-react";
import { fmtPct, fmtW } from "@/lib/format";
import { iconFor } from "@/lib/icons";
import type { LiveFlow, LiveSummary } from "@/lib/types";

interface Pt {
  x: number;
  y: number;
}

function useIsNarrow() {
  const [narrow, setNarrow] = useState(() => window.matchMedia("(max-width: 640px)").matches);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 640px)");
    const fn = () => setNarrow(mq.matches);
    mq.addEventListener("change", fn);
    return () => mq.removeEventListener("change", fn);
  }, []);
  return narrow;
}

function angles(n: number, maxDeg: number): number[] {
  if (n <= 1) return [0];
  const m = Math.min(maxDeg, 15 * (n - 1));
  return Array.from({ length: n }, (_, i) => ((-m + (2 * m * i) / (n - 1)) * Math.PI) / 180);
}

function speed(w: number): number {
  const d = 4.2 - Math.log10(Math.max(w, 10)) * 0.85;
  return Math.round(Math.max(0.8, Math.min(4, d)) * 4) / 4;
}

function short(name: string, max: number) {
  return name.length > max ? `${name.slice(0, max - 1)}…` : name;
}

interface NodeProps {
  flow: LiveFlow;
  pos: Pt;
  hub: Pt;
  vertical: boolean;
  r: number;
}

function FlowNode({ flow, pos, hub, vertical, r }: NodeProps) {
  const Icon = iconFor(flow.icon);
  const w = flow.power_w ?? 0;
  const active = flow.available && w > 5;
  const ctrl = vertical ? { x: pos.x, y: (pos.y + hub.y) / 2 } : { x: (pos.x + hub.x) / 2, y: pos.y };
  const d =
    flow.direction === "in"
      ? `M ${pos.x} ${pos.y} Q ${ctrl.x} ${ctrl.y} ${hub.x} ${hub.y}`
      : `M ${hub.x} ${hub.y} Q ${ctrl.x} ${ctrl.y} ${pos.x} ${pos.y}`;
  const dur = speed(w);
  const width = 2 + Math.min(5, w / 1500);
  const labelAbove = vertical && flow.direction === "in";
  const ly = labelAbove ? pos.y - r - 30 : pos.y + r + 24;
  return (
    <g data-testid={`flow-node-${flow.flow_id}`}>
      <path d={d} fill="none" stroke="#1E2F65" strokeWidth={width + 4} strokeLinecap="round" />
      <path
        d={d}
        fill="none"
        stroke={flow.available ? flow.color : "#4B5563"}
        strokeOpacity={active ? 0.85 : 0.3}
        strokeWidth={width}
        strokeLinecap="round"
        strokeDasharray={flow.available ? undefined : "4 8"}
        className={active ? "flow-line-active" : undefined}
      />
      {active &&
        [0, 1, 2].map((i) => (
          <circle key={i} r={4.5 + Math.min(2.5, w / 3000)} fill={flow.color} className="flow-dot" filter="url(#dot-glow)">
            <animateMotion dur={`${dur}s`} repeatCount="indefinite" begin={`${(-i * dur) / 3}s`} path={d} />
          </circle>
        ))}
      <circle cx={pos.x} cy={pos.y} r={r + 7} fill={flow.color} opacity={active ? 0.14 : 0.05} />
      <circle cx={pos.x} cy={pos.y} r={r} fill="#111D42" stroke={flow.color} strokeWidth={2.5} strokeOpacity={active ? 1 : 0.45} />
      <Icon x={pos.x - r * 0.45} y={pos.y - r * 0.45} width={r * 0.9} height={r * 0.9} color={flow.color} strokeWidth={1.8} />
      <text x={pos.x} y={ly} textAnchor="middle" fill="#8EA8C3" fontSize={vertical ? 17 : 15} fontWeight={600} fontFamily="DM Sans Variable">
        {short(flow.name, vertical ? 11 : 18)}
      </text>
      <text
        x={pos.x}
        y={ly + (vertical ? 22 : 21)}
        textAnchor="middle"
        fill={flow.available ? "#F0F4F8" : "#F87171"}
        fontSize={vertical ? 19 : 17}
        fontWeight={700}
        fontFamily="JetBrains Mono Variable"
        data-testid={`flow-node-power-${flow.flow_id}`}
      >
        {fmtW(flow.power_w)}
      </text>
    </g>
  );
}

interface Props {
  flows: LiveFlow[];
  summary: LiveSummary | null;
}

export default function FlowDiagram({ flows, summary }: Props) {
  const vertical = useIsNarrow();
  const W = vertical ? 600 : 1000;
  const H = vertical ? 900 : 640;
  const hub: Pt = vertical ? { x: 300, y: 450 } : { x: 500, y: 320 };
  const ins = flows.filter((f) => f.direction === "in");
  const outs = flows.filter((f) => f.direction === "out");
  const maxN = Math.max(ins.length, outs.length);
  const r = maxN > 6 ? 28 : maxN > 4 ? 34 : 40;

  const place = (list: LiveFlow[], side: "in" | "out"): Pt[] =>
    angles(list.length, 64).map((a) => {
      if (vertical) {
        const sign = side === "in" ? -1 : 1;
        return { x: hub.x + 245 * Math.sin(a), y: hub.y + sign * 320 * Math.cos(a) * (list.length > 3 ? 0.92 : 1) };
      }
      const sign = side === "in" ? -1 : 1;
      return { x: hub.x + sign * 390 * Math.cos(a), y: hub.y + 245 * Math.sin(a) };
    });
  const inPos = place(ins, "in");
  const outPos = place(outs, "out");

  return (
    <div className="diagram-bg relative overflow-hidden rounded-xl border border-[#1E2F65] bg-[#0E1838] panel-shadow" data-testid="flow-diagram">
      <div className="pointer-events-none absolute left-4 top-3 flex gap-4 text-[11px] font-medium uppercase tracking-wider text-[#8EA8C3]">
        <span>{vertical ? "↓ Zuflüsse" : "← Zuflüsse"}</span>
      </div>
      <div className="pointer-events-none absolute right-4 top-3 text-[11px] font-medium uppercase tracking-wider text-[#8EA8C3]">
        {vertical ? "" : "Abflüsse →"}
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full" role="img" aria-label="Energieflussdiagramm">
        <defs>
          <filter id="dot-glow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="3" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <radialGradient id="hub-grad" cx="50%" cy="40%" r="60%">
            <stop offset="0%" stopColor="#2A44A0" />
            <stop offset="100%" stopColor="#1C2E6A" />
          </radialGradient>
        </defs>
        {ins.map((f, i) => (
          <FlowNode key={f.flow_id} flow={f} pos={inPos[i]} hub={hub} vertical={vertical} r={r} />
        ))}
        {outs.map((f, i) => (
          <FlowNode key={f.flow_id} flow={f} pos={outPos[i]} hub={hub} vertical={vertical} r={r} />
        ))}
        <g data-testid="flow-hub">
          <circle cx={hub.x} cy={hub.y} r={96} fill="#2563EB" opacity={0.25} className="animate-hub-glow" />
          <circle cx={hub.x} cy={hub.y} r={82} fill="url(#hub-grad)" stroke="#2563EB" strokeWidth={3} />
          <House x={hub.x - 15} y={hub.y - 58} width={30} height={30} color="#93C5FD" strokeWidth={1.8} />
          <text x={hub.x} y={hub.y - 6} textAnchor="middle" fill="#93C5FD" fontSize={14} fontWeight={600} fontFamily="DM Sans Variable">
            Verbrauch
          </text>
          <text
            x={hub.x}
            y={hub.y + 22}
            textAnchor="middle"
            fill="#FFFFFF"
            fontSize={24}
            fontWeight={800}
            fontFamily="JetBrains Mono Variable"
            data-testid="flow-hub-consumption"
          >
            {fmtW(summary?.consumption_w ?? null)}
          </text>
          <text x={hub.x} y={hub.y + 46} textAnchor="middle" fill="#93C5FD" fontSize={13} fontFamily="DM Sans Variable">
            Autarkie {fmtPct(summary?.autarky_pct ?? null)}
          </text>
        </g>
        {flows.length === 0 && (
          <text x={hub.x} y={hub.y + 140} textAnchor="middle" fill="#8EA8C3" fontSize={16}>
            Keine Flüsse konfiguriert
          </text>
        )}
      </svg>
    </div>
  );
}
