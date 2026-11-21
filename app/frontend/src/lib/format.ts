import type { Category, Method } from "@/lib/types";

const nf0 = new Intl.NumberFormat("de-DE", { maximumFractionDigits: 0 });
const nf2 = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const nf1 = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const smallPower = new Intl.NumberFormat("de-DE", { maximumSignificantDigits: 3 });
const nf3 = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 3, maximumFractionDigits: 3 });

export const NA = "n. v.";

export function fmtW(w: number | null | undefined): string {
  if (w === null || w === undefined) return NA;
  if (w === 0) return "0 W";
  if (Math.abs(w) < 1) return `${smallPower.format(w)} W`;
  if (Math.abs(w) >= 1000) return `${nf2.format(w / 1000)} kW`;
  return `${nf0.format(w)} W`;
}

export function fmtKwh(k: number | null | undefined): string {
  if (k === null || k === undefined) return NA;
  return `${(Math.abs(k) < 10 ? nf3 : nf2).format(k)} kWh`;
}

export function fmtPct(p: number | null | undefined): string {
  if (p === null || p === undefined) return NA;
  return `${nf0.format(p)} %`;
}

export function fmtHz(h: number | null | undefined): string {
  if (h === null || h === undefined) return NA;
  return `${nf3.format(h)} Hz`;
}

export function fmtNum1(n: number): string {
  return nf1.format(n);
}

const dtf = new Intl.DateTimeFormat("de-DE", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});
const tf = new Intl.DateTimeFormat("de-DE", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

export function fmtDateTime(iso: string): string {
  return dtf.format(new Date(iso));
}

export function fmtTime(iso: string): string {
  return tf.format(new Date(iso));
}

/** "YYYY-MM-DDTHH:MM" (server-local) → "DD.MM.YYYY HH:MM" without timezone shifting. */
export function fmtLocal(local: string): string {
  const [d, t] = local.split("T");
  const [y, m, day] = d.split("-");
  return `${day}.${m}.${y} ${t ?? ""}`.trim();
}

export function fmtDuration(seconds: number): string {
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
  if (seconds < 86400) return `${fmtNum1(seconds / 3600)} h`;
  return `${fmtNum1(seconds / 86400)} Tage`;
}

export const CATEGORY_LABELS: Record<Category, string> = {
  pv: "Photovoltaik",
  generator: "Generator / BHKW",
  grid: "Netz",
  battery: "Speicher",
  heatpump: "Wärmepumpe",
  ev: "E-Mobilität",
  consumer: "Verbraucher",
  custom: "Benutzerdefiniert",
};

export const METHOD_LABELS: Record<Method, string> = {
  counter_delta: "Zählerdelta",
  phase_sum: "Phasensumme",
  power_integral: "Leistungsintegration",
  run_estimate: "RUN-Schätzung",
  unavailable: "Nicht verfügbar",
  not_applicable: "Nicht belegt",
};

export const DIRECTION_LABELS = { in: "Zufluss", out: "Abfluss" } as const;
