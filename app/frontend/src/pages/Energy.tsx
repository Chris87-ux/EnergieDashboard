import { t } from "@/lib/i18n";
import { useEffect, useState } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";
import ConsumerGroupsOverview from "@/components/ConsumerGroupsOverview";
import GridConnection from "@/components/GridConnection";
import EnergyTable from "@/components/EnergyTable";
import MethodBadge from "@/components/MethodBadge";
import RangePicker from "@/components/RangePicker";
import { ApiError } from "@/lib/api";
import { fmtDuration, fmtKwh, fmtLocal, fmtPct } from "@/lib/format";
import { usePresets, useEnergy, useFlows, useLive, type Range } from "@/lib/queries";

export default function Energy() {
  const presets = usePresets();
  const live = useLive();
  const configuration = useFlows();
  const [range, setRange] = useState<Range | null>(null);
  const [preset, setPreset] = useState<string | undefined>("today");

  // Default to the server's "today" once presets arrive (server-anchored, not browser date math).
  useEffect(() => {
    const selected = presets.data?.find((item) => item.key === preset);
    if (selected && (range?.start !== selected.start || range?.end !== selected.end)) {
      setRange({ start: selected.start, end: selected.end });
    }
  }, [presets.data, preset, range]);

  const energy = useEnergy(range);
  const report = energy.isError ? undefined : energy.data;
  const errMsg =
    energy.error instanceof ApiError
      ? String((energy.error.body as { detail?: unknown })?.detail ?? t("Fehler bei der Berechnung"))
      : energy.isError
        ? t("Backend nicht erreichbar")
        : null;

  return (
    <>
      <section className="space-y-1">
        <p className="text-sm font-medium text-[var(--primary)]">{t("Energie-Bilanz")}</p>
        <h1 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl" data-testid="energy-title">{t("Gesamt- und Phasenenergie in kWh")}</h1>
        <p className="max-w-3xl text-sm text-[#8EA8C3]">
          {t("Produktion ohne Netzbezug und Verbrauch ohne Lieferung oder Speicherladung. AC/DC-Messgrenzen und unvollständige Werte sind gekennzeichnet. Zählerdeltas mit Reset-Erkennung, Summe vollständiger Phasen oder Integration historischer Wirkleistung – fehlende Daten werden als Lücke bzw. „Nicht verfügbar“ markiert.")}</p>
      </section>

      <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 panel-shadow">
        <RangePicker
          value={range}
          presets={presets.data ?? []}
          activePreset={preset}
          onChange={(r, key) => {
            setRange(r);
            setPreset(key);
          }}
        />
      </section>

      {errMsg && (
        <div className="rounded-xl border border-[#7F1D1D] bg-[#450A0A]/60 p-3 text-sm text-[#FECACA]" data-testid="energy-error">
          {errMsg}
        </div>
      )}

      <GridConnection data={live.data} period={report?.totals} periodLabel="Zeitraum" energyOnly />
      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" data-testid="energy-summary">
        <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 panel-shadow">
          <div className="text-xs text-[#8EA8C3]">{t("Produktion gesamt")}</div>
          <div className="mt-1 font-mono text-xl font-extrabold sm:text-2xl" data-testid="energy-sum-in">{report ? fmtKwh(report.totals.production_kwh) : "—"}</div>
        </div>
        <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 panel-shadow">
          <div className="text-xs text-[#8EA8C3]">{t("Verbrauch gesamt")}</div>
          <div className="mt-1 font-mono text-xl font-extrabold sm:text-2xl" data-testid="energy-sum-out">{report ? fmtKwh(report.totals.consumption_kwh) : "—"}</div>
        </div>
        <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 panel-shadow">
          <div className="text-xs text-[#8EA8C3]">{t("Zeitraum (")}{report?.timezone ?? "—"})</div>
          <div className="mt-1 font-mono text-xs font-semibold sm:text-sm" data-testid="energy-range-label">
            {report ? `${fmtLocal(report.start_local)} – ${fmtLocal(report.end_local)}` : "—"}
          </div>
        </div>
        <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 panel-shadow">
          <div className="text-xs text-[#8EA8C3]">{t("Auflösung / Lückenschwelle")}</div>
          <div className="mt-1 font-mono text-sm font-semibold" data-testid="energy-resolution">
            {report ? `${fmtDuration(report.step_s)} / ${fmtDuration(report.gap_threshold_s)}` : "—"}
          </div>
          {report?.totals.incomplete && (
            <div className="mt-1 flex items-center gap-1 text-[11px] text-[#FBBF24]" data-testid="energy-incomplete-hint">
              <AlertTriangle className="size-3" /> {t(" Datenlücken erkannt")}</div>
          )}
        </div>
      </section>

      <section className="grid grid-cols-2 gap-3"><div className="rounded-xl border border-border bg-card p-4">{t("Autarkiegrad · Zeitraum")}<p className="font-mono text-xl" data-testid="energy-autarky">{fmtPct(report?.totals.autarky_pct)}</p></div><div className="rounded-xl border border-border bg-card p-4">{t("Eigenverbrauch · Zeitraum")}<p className="font-mono text-xl" data-testid="energy-self-consumption">{fmtPct(report?.totals.self_consumption_pct)}</p></div></section>
      {report && <details className="text-xs text-muted-foreground"><summary>{t("Bilanzhinweise")}{report.totals.production_estimated ? t(" · Produktion geschätzt") : ""}</summary>{report.totals.notes.map(n=><p key={n}>{n}</p>)}</details>}
      <section className="flex flex-wrap items-center gap-3 text-xs text-[#8EA8C3]" data-testid="energy-legend">
        <span className="font-medium text-[#F0F4F8]">{t("Berechnungsmethode:")}</span>
        <MethodBadge method="counter_delta" />
        <MethodBadge method="phase_sum" />
        <MethodBadge method="power_integral" />
        <MethodBadge method="run_estimate" />
        <MethodBadge method="unavailable" />
        <span className="flex items-center gap-1"><AlertTriangle className="size-3.5 text-[#FBBF24]" /> {t(" unvollständig")}</span>
        <span className="flex items-center gap-1"><RotateCcw className="size-3.5 text-[var(--primary)]" /> {t(" Zähler-Reset")}</span>
      </section>

      {report && report.errors.length > 0 && (
        <div className="rounded-xl border border-[#78350F] bg-[#78350F]/30 p-3 text-xs text-[#FDE68A]" data-testid="energy-source-errors">
          {report.errors.map((e) => (
            <div key={e}>{e}</div>
          ))}
        </div>
      )}

      <ConsumerGroupsOverview energy={report?.consumer_groups} period="Zeitraum" energyOnly/>
      {energy.isFetching && !report && <div className="text-sm text-[#8EA8C3]">{t("Berechne Energiewerte…")}</div>}
      {report && [{ id: null, name: t("Hauptebene") }, ...(configuration.data ?? []).filter((flow) => flow.kind === "node").map((node) => ({ id: node.id, name: node.name }))].map((group) => {
        const flows = report.flows.filter((flow) => flow.parent_id === group.id);
        if (!flows.length) return null;
        return <details key={group.id ?? "root"} open className="space-y-3">
          <summary className="cursor-pointer font-heading font-semibold">{group.name}</summary>
          <EnergyTable report={{ ...report, flows }} />
        </details>;
      })}
    </>
  );
}
