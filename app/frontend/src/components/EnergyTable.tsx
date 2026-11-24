import { t } from "@/lib/i18n";
import { Fragment, useState } from "react";
import { AlertTriangle, ChevronDown, RotateCcw } from "lucide-react";
import MethodBadge from "@/components/MethodBadge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { fmtDateTime, fmtKwh, fmtPct } from "@/lib/format";
import { iconFor } from "@/lib/icons";
import { PHASES, type EnergyReport, type EnergyValue, type Gap } from "@/lib/types";
import { cn } from "@/lib/utils";

function GapBar({ start, end, gaps, color, testid }: { start: string; end: string; gaps: Gap[]; color: string; testid: string }) {
  const a = new Date(start).getTime();
  const b = new Date(end).getTime();
  const span = Math.max(1, b - a);
  return (
    <div className="relative h-2 w-full min-w-24 overflow-hidden rounded-full" style={{ background: `${color}55` }} data-testid={testid}>
      {gaps.map((g, i) => {
        const l = Math.max(0, (new Date(g.start).getTime() - a) / span);
        const r = Math.min(1, (new Date(g.end).getTime() - a) / span);
        return (
          <span
            key={i}
            className="absolute inset-y-0 bg-[#F87171]"
            style={{ left: `${l * 100}%`, width: `${Math.max(0.6, (r - l) * 100)}%` }}
            title={`${fmtDateTime(g.start)} – ${fmtDateTime(g.end)}`}
          />
        );
      })}
    </div>
  );
}

function Cell({ v, testid }: { v: EnergyValue; testid: string }) {
  if (v.method === "not_applicable") {
    return <span className="text-xs text-[#8EA8C3]" data-testid={testid}>{t("— nicht belegt")}</span>;
  }
  return (
    <div className="flex flex-col items-start gap-1" data-testid={testid}>
      <span className={cn("font-mono text-sm font-semibold", v.kwh === null && "text-[#F87171]")}>{fmtKwh(v.kwh)}</span>
      <div className="flex items-center gap-1">
        <MethodBadge method={v.method} />
        {!v.complete && v.method !== "unavailable" && <AlertTriangle className="size-3.5 text-[#FBBF24]" aria-label={t("Lücken")} />}
        {v.resets > 0 && <RotateCcw className="size-3.5 text-[var(--primary)]" aria-label={t("Zähler-Reset")} />}
      </div>
    </div>
  );
}

export default function EnergyTable({ report }: { report: EnergyReport }) {
  const [open, setOpen] = useState<string | null>(null);
  const maxKwh = Math.max(1, ...report.flows.map((f) => f.total.kwh ?? 0));
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] panel-shadow">
      <Table data-testid="energy-table">
        <TableHeader>
          <TableRow className="border-[var(--border)] hover:bg-transparent">
            <TableHead className="text-[#8EA8C3]">{t("Fluss")}</TableHead>
            <TableHead className="text-[#8EA8C3]">{t("Gesamt")}</TableHead>
            {PHASES.map((p) => (
              <TableHead key={p} className="text-[#8EA8C3]">{p}</TableHead>
            ))}
            <TableHead className="min-w-40 text-[#8EA8C3]">{t("Abdeckung &amp; Lücken")}</TableHead>
            <TableHead />
          </TableRow>
        </TableHeader>
        <TableBody>
          {report.flows.map((f) => {
            const Icon = iconFor(f.icon);
            const isOpen = open === f.flow_id;
            const allGaps = f.total.gaps;
            return (
              <Fragment key={f.flow_id}>
                <TableRow className="border-[var(--border)] hover:bg-muted/60" data-testid={`energy-row-${f.flow_id}`}>
                  <TableCell>
                    <div className="flex items-center gap-2.5">
                      <span className="grid size-8 shrink-0 place-items-center rounded-md" style={{ background: `${f.color}22` }}>
                        <Icon className="size-4" style={{ color: f.color }} />
                      </span>
                      <div>
                        <div className="font-medium">{f.name}</div>
                        <div className="text-[11px] text-[#8EA8C3]">
                          {f.direction === "in" ? t("Produktion") : t("Verbrauch")} · {f.electrical_side === "dc" ? t("DC · separat") : PHASES.every(p=>f.phases[p].method === "not_applicable") ? t("AC · Gesamtwert") : f.energy_phase_mode === "three" ? t("3-phasig") : `AC · ${f.energy_phase}`}
                        </div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1.5">
                      <Cell v={f.total} testid={`energy-total-${f.flow_id}`} />
                      <div className="h-1 w-28 overflow-hidden rounded-full bg-[var(--background)]">
                        <div className="h-full rounded-full" style={{ width: `${((f.total.kwh ?? 0) / maxKwh) * 100}%`, background: f.color }} />
                      </div>
                    </div>
                  </TableCell>
                  {PHASES.map((p) => (
                    <TableCell key={p}>
                      <Cell v={f.phases[p]} testid={`energy-phase-${f.flow_id}-${p}`} />{f.estimated_phases?.includes(p)&&<span className="text-xs text-amber-300">{t("Symmetrisch berechnet")}</span>}
                    </TableCell>
                  ))}
                  <TableCell>
                    <div className="space-y-1">
                      <GapBar start={report.start} end={report.effective_end} gaps={allGaps} color={f.color} testid={`energy-gapbar-${f.flow_id}`} />
                      <div className="text-[11px] text-[#8EA8C3]" data-testid={`energy-coverage-${f.flow_id}`}>
                        {fmtPct(f.total.coverage * 100)} {t(" abgedeckt")}{allGaps.length > 0 && <span className="text-[#FBBF24]"> · {allGaps.length} {t(" Lücke(n)")}</span>}
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <button
                      type="button"
                      className="grid size-7 place-items-center rounded-md text-[#8EA8C3] transition-colors hover:bg-accent hover:text-white"
                      onClick={() => setOpen(isOpen ? null : f.flow_id)}
                      data-testid={`energy-row-toggle-${f.flow_id}`}
                      aria-label="Details"
                    >
                      <ChevronDown className={cn("size-4 transition-transform duration-200", isOpen && "rotate-180")} />
                    </button>
                  </TableCell>
                </TableRow>
                {isOpen && (
                  <TableRow className="border-[var(--border)] bg-[var(--card)] hover:bg-[var(--card)]" data-testid={`energy-row-details-${f.flow_id}`}>
                    <TableCell colSpan={7} className="whitespace-normal">
                      <div className="grid gap-4 py-2 text-xs md:grid-cols-2">
                        <div className="space-y-1">
                          <div className="font-semibold text-[#F0F4F8]">{t("Berechnung")}</div>
                          <div className="text-[#8EA8C3]">{t("Gesamt: ")}{f.total.note || "—"}</div>
                          {PHASES.map((p) => (
                            <div key={p} className="text-[#8EA8C3]">
                              {p}: {f.phases[p].note || "—"}
                            </div>
                          ))}
                        </div>
                        <div className="space-y-1">
                          <div className="font-semibold text-[#F0F4F8]">{t("Datenlücken (Gesamt)")}</div>
                          {allGaps.length === 0 ? (
                            <div className="text-[#34D399]">{t("Keine Lücken erkannt")}</div>
                          ) : (
                            <ul className="max-h-40 space-y-0.5 overflow-auto font-mono text-[#FBBF24]">
                              {allGaps.map((g, i) => (
                                <li key={i}>
                                  {fmtDateTime(g.start)} – {fmtDateTime(g.end)}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      </div>
                    </TableCell>
                  </TableRow>
                )}
              </Fragment>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
