import { language, changeLanguage, t, type Language } from "@/lib/i18n";
export default function LanguageSelector() {
  return <select data-testid="language-selector" aria-label={t("Sprache")} title={t("Sprache")} value={language} onChange={event => changeLanguage(event.target.value as Language)} className="max-w-28 rounded-md border border-border bg-card p-1.5 text-xs text-foreground"><option value="de">Deutsch</option><option value="en">English</option></select>;
}
