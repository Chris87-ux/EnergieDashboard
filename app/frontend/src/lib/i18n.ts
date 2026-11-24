import catalog from "./en.json";

export type Language = "de" | "en";
const translations: Record<string, string> = catalog;
const key = "energieboard.language";
export function readLanguage(): Language {
  if (typeof window === "undefined") return "de";
  const requested = new URL(window.location.href).searchParams.get("lang");
  if (requested === "de" || requested === "en") return requested;
  try { return window.localStorage.getItem(key) === "en" ? "en" : "de"; }
  catch { return "de"; }
}
export const language = readLanguage();
export const locale = language === "en" ? "en-GB" : "de-DE";
const decode = (text: string) => text.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#39;/g, "'");
/** Translate built-in text only. Interpolated names/IDs are kept verbatim. */
export function t(source: string, ...values: unknown[]): string {
  const text = language === "en" ? translations[source] ?? source : decode(source);
  return text.replace(/\{(\d+)\}/g, (placeholder, index: string) => Number(index) < values.length ? String(values[Number(index)]) : placeholder);
}
export function changeLanguage(next: Language): void {
  if (next === language) return;
  if (!window.confirm(t("Beim Sprachwechsel wird die Seite neu geladen. Ungespeicherte Änderungen können verloren gehen. Fortfahren?"))) return;
  try { window.localStorage.setItem(key, next); } catch { /* URL still works when storage is blocked. */ }
  const url = new URL(window.location.href);
  url.searchParams.set("lang", next);
  window.location.assign(url.href);
}
export function docsUrl(german: string, english: string): string {
  return "https://github.com/Chris87-ux/EnergieDashboard/blob/main/" + (language === "en" ? "docs/en/" + english : german);
}
if (typeof document !== "undefined") {
  document.documentElement.lang = language;
  document.title = "Energieboard · " + t("Energiefluss");
}
