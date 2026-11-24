import { t, locale, language } from "@/lib/i18n";
import type { Category, Method } from "@/lib/types";

const nf0 = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
const nf2 = new Intl.NumberFormat(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const nf1 = new Intl.NumberFormat(locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const smallPower = new Intl.NumberFormat(locale, { maximumSignificantDigits: 3 });
const nf3 = new Intl.NumberFormat(locale, { minimumFractionDigits: 3, maximumFractionDigits: 3 });

export const NA = t("n. v.");

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

const dtf = new Intl.DateTimeFormat(locale, {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});
const tf = new Intl.DateTimeFormat(locale, { hour: "2-digit", minute: "2-digit", second: "2-digit" });

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
  return (language === "en" ? `${day}/${m}/${y} ${t ?? ""}` : `${day}.${m}.${y} ${t ?? ""}`).trim();
}

export function fmtDuration(seconds: number): string {
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
  if (seconds < 86400) return `${fmtNum1(seconds / 3600)} h`;
  return t("{0} Tage", fmtNum1(seconds / 86400));
}

export const CATEGORY_LABELS: Record<Category, string> = {
  pv: t("Photovoltaik"),
  generator: t("Generator / BHKW"),
  grid: t("Netz"),
  battery: t("Speicher"),
  heatpump: t("Wärmepumpe"),
  ev: t("E-Mobilität"),
  consumer: t("Verbraucher"),
  custom: t("Benutzerdefiniert"),
};

export const METHOD_LABELS: Record<Method, string> = {
  counter_delta: t("Zählerdelta"),
  phase_sum: t("Phasensumme"),
  power_integral: t("Leistungsintegration"),
  run_estimate: t("RUN-Schätzung"),
  unavailable: t("Nicht verfügbar"),
  not_applicable: t("Nicht belegt"),
};

export const DIRECTION_LABELS = { in: t("Produktion"), out: t("Verbrauch") } as const;
