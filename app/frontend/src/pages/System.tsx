import { t, locale } from "@/lib/i18n";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Database, Radio, Save, Server, Settings2, XCircle } from "lucide-react";
import { toast } from "sonner";
import LxcGuide from "@/components/LxcGuide";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ApiError, apiPost, apiPut } from "@/lib/api";
import { fmtDateTime } from "@/lib/format";
import { useRecorder, useSettings } from "@/lib/queries";
import type { SettingsOut, TestResult } from "@/lib/types";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

function Panel({ title, icon: Icon, children, testid }: { title: string; icon: LucideIcon; children: React.ReactNode; testid: string }) {
  return (
    <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 panel-shadow" data-testid={testid}>
      <div className="mb-4 flex items-center gap-2">
        <Icon className="size-5 text-[var(--primary)]" />
        <h2 className="font-heading text-lg font-semibold">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function F({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs font-medium text-[#8EA8C3]">{label}</Label>
      {children}
      {hint && <p className="text-[11px] text-[#8EA8C3]/80">{hint}</p>}
    </div>
  );
}

function TestBox({ result, testid }: { result: TestResult | null; testid: string }) {
  if (!result) return null;
  return (
    <div
      data-testid={testid}
      className={cn(
        "mt-3 rounded-lg border p-3 text-xs",
        result.ok ? "border-[#065F46] bg-[#064E3B]/50 text-[#A7F3D0]" : "border-[#7F1D1D] bg-[#450A0A]/60 text-[#FECACA]",
      )}
    >
      <div className="flex items-center gap-1.5 font-semibold">
        {result.ok ? <CheckCircle2 className="size-4" /> : <XCircle className="size-4" />}
        {result.message}
      </div>
      {result.details.length > 0 && (
        <ul className="mt-1.5 max-h-32 space-y-0.5 overflow-auto font-mono text-[11px] opacity-90">
          {result.details.map((d) => (
            <li key={d}>{d}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

const RECORDER_LABELS: Record<string, string> = {
  idle: t("Bereit"), disabled: t("Deaktiviert"), waiting: t("Wartet"), recording: t("Zeichnet auf"), error: t("Fehler"),
};

function SettingsForm({ initial }: { initial: SettingsOut }) {
  const qc = useQueryClient();
  const [form, setForm] = useState<SettingsOut>(initial);
  const [influxResult, setInfluxResult] = useState<TestResult | null>(null);
  const recorder = useRecorder();
  const rec = recorder.isError ? undefined : recorder.data;

  const upd = <K extends keyof SettingsOut>(k: K, v: SettingsOut[K]) => setForm((f) => ({ ...f, [k]: v }));
  const inf = <K extends keyof SettingsOut["influx"]>(k: K, v: SettingsOut["influx"][K]) => setForm((f) => ({ ...f, influx: { ...f.influx, [k]: v } }));
  const recSet = <K extends keyof SettingsOut["recorder"]>(k: K, v: SettingsOut["recorder"][K]) => setForm((f) => ({ ...f, recorder: { ...f.recorder, [k]: v } }));

  const save = useMutation({
    mutationFn: (body: SettingsOut) => apiPut<SettingsOut>("/settings", body),
    onSuccess: (data) => {
      qc.setQueryData(["settings"], data);
      setForm(data);
      qc.invalidateQueries({ queryKey: ["live"] });
      qc.invalidateQueries({ queryKey: ["energy"] });
      qc.invalidateQueries({ queryKey: ["presets"] });
      qc.invalidateQueries({ queryKey: ["recorder"] });
      toast.success(t("Einstellungen gespeichert"));
    },
    onError: (e) => {
      const d = e instanceof ApiError ? JSON.stringify((e.body as { detail?: unknown })?.detail ?? "") : String(e);
      toast.error(t("Speichern fehlgeschlagen: {0}", d));
    },
  });
  const testInflux = useMutation({
    mutationFn: (body: SettingsOut) => apiPost<TestResult>("/settings/test/influx", body),
    onSuccess: setInfluxResult,
    onError: () => setInfluxResult({ ok: false, message: t("Test fehlgeschlagen"), details: [] }),
  });

  const num = (v: string) => (v === "" ? 0 : Number(v));

  return (
    <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
      <div className="space-y-6">
        <Panel title={t("Allgemein")} icon={Settings2} testid="settings-general-panel">
          <div className="grid gap-4 sm:grid-cols-2">
            <F label={t("Name der Anlage")}>
              <Input value={form.site_name} onChange={(e) => upd("site_name", e.target.value)} data-testid="settings-site-name-input" />
            </F>
            <F label={t("Zeitzone")} hint={t("Basis für „Heute“, Presets und Zeitraumauswahl")}>
              <Input value={form.timezone} onChange={(e) => upd("timezone", e.target.value)} data-testid="settings-timezone-input" />
            </F>
            <F label={t("Live-Aktualisierung (s)")}>
              <Input type="number" min={1} value={form.live_poll_s} onChange={(e) => upd("live_poll_s", num(e.target.value))} data-testid="settings-poll-input" />
            </F>
            <F label={t("Lückenschwelle (min)")} hint={t("Längere Pausen zwischen Messwerten gelten als Lücke")}>
              <Input type="number" min={1} value={form.gap_threshold_min} onChange={(e) => upd("gap_threshold_min", num(e.target.value))} data-testid="settings-gap-input" />
            </F>
          </div>
        </Panel>

        <Panel title={t("Aufzeichnungs-Dienst (Recorder)")} icon={Database} testid="settings-recorder-panel">
          <p className="mb-3 text-xs text-[#8EA8C3]">{t("Die normalisierten Messwerte werden aus ioBroker, MQTT und Modbus TCP aufgezeichnet. RUN-Laufzeiten und Speicherleistung gehen ab diesem Zeitpunkt in die lokale Historie ein.")}</p>
          <div className="flex flex-wrap items-end gap-4">
            <label className="flex items-center gap-2 text-sm">
              <Checkbox checked={form.recorder.enabled} onCheckedChange={(c) => recSet("enabled", c === true)} data-testid="settings-recorder-enabled-checkbox" />
              {t("Aufzeichnung aktiv")}</label>
            <F label={t("Intervall (s)")}>
              <Input type="number" min={5} className="w-28" value={form.recorder.interval_s} onChange={(e) => recSet("interval_s", num(e.target.value))} data-testid="settings-recorder-interval-input" />
            </F>
          </div>
          <div className="mt-4 rounded-lg border border-[var(--border)] bg-[var(--card)] p-3 text-xs" data-testid="recorder-status">
            <div className="flex items-center justify-between">
              <span className="font-semibold" data-testid="recorder-status-state">{rec ? RECORDER_LABELS[rec.state] : "—"}</span>
              <span className="font-mono text-[#93C5FD]" data-testid="recorder-status-samples">{rec ? t("{0} Messwerte", rec.samples_total.toLocaleString(locale)) : ""}</span>
            </div>
            <div className="mt-1 text-[#8EA8C3]" data-testid="recorder-status-message">{rec?.message ?? t("Status nicht verfügbar")}</div>
            {rec?.last_run && <div className="mt-1 text-[#8EA8C3]">{t("Letzter Lauf: ")}{fmtDateTime(rec.last_run)}</div>}
            {rec?.last_error && <div className="mt-1 text-[#FECACA]">{t("Letzter Fehler: ")}{rec.last_error}</div>}
            {rec && rec.recorded_dps.length > 0 && (
              <div className="mt-2 max-h-24 overflow-auto font-mono text-[11px] text-[#BFDBFE]">{rec.recorded_dps.join(" · ")}</div>
            )}
          </div>
        </Panel>
      </div>

      <div className="space-y-6">
        <Panel title={t("InfluxDB (Historie)")} icon={Database} testid="settings-influx-panel">
          <label className="mb-4 flex items-center gap-2 text-sm">
            <Checkbox checked={form.influx.enabled} onCheckedChange={(c) => inf("enabled", c === true)} data-testid="settings-influx-enabled-checkbox" />
            {t("Bestehende Historie aus InfluxDB lesen")}</label>
          <div className="grid gap-4 sm:grid-cols-2">
            <F label="Version">
              <Select value={form.influx.version} onValueChange={(v: string) => inf("version", v as "v1" | "v2")}>
                <SelectTrigger className="w-full" data-testid="settings-influx-version-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="v1" data-testid="settings-influx-version-v1">InfluxDB 1.x (InfluxQL)</SelectItem>
                  <SelectItem value="v2" data-testid="settings-influx-version-v2">InfluxDB 2.x (Flux)</SelectItem>
                </SelectContent>
              </Select>
            </F>
            <F label="URL">
              <Input value={form.influx.url} onChange={(e) => inf("url", e.target.value)} data-testid="settings-influx-url-input" />
            </F>
            {form.influx.version === "v1" ? (
              <>
                <F label={t("Datenbank")}>
                  <Input value={form.influx.database} onChange={(e) => inf("database", e.target.value)} data-testid="settings-influx-db-input" />
                </F>
                <F label={t("Benutzer")}>
                  <Input value={form.influx.username} onChange={(e) => inf("username", e.target.value)} data-testid="settings-influx-user-input" />
                </F>
                <F label={t("Passwort")} hint={form.influx_password_set ? t("Gespeichert – leer lassen, um es beizubehalten") : undefined}>
                  <Input type="password" value={form.influx.password} onChange={(e) => inf("password", e.target.value)} placeholder={form.influx_password_set ? "••••••••" : ""} data-testid="settings-influx-password-input" />
                </F>
              </>
            ) : (
              <>
                <F label="Organisation">
                  <Input value={form.influx.org} onChange={(e) => inf("org", e.target.value)} data-testid="settings-influx-org-input" />
                </F>
                <F label="Bucket">
                  <Input value={form.influx.bucket} onChange={(e) => inf("bucket", e.target.value)} data-testid="settings-influx-bucket-input" />
                </F>
                <F label="API-Token" hint={form.influx_token_set ? t("Gespeichert – leer lassen, um es beizubehalten") : undefined}>
                  <Input type="password" value={form.influx.token} onChange={(e) => inf("token", e.target.value)} placeholder={form.influx_token_set ? "••••••••" : ""} data-testid="settings-influx-token-input" />
                </F>
              </>
            )}
            <F label={t("Feldname")} hint={t("ioBroker-influxdb-Adapter: „value“, Measurement = Objekt-ID")}>
              <Input value={form.influx.field} onChange={(e) => inf("field", e.target.value)} data-testid="settings-influx-field-input" />
            </F>
          </div>
          <Button variant="outline" className="mt-4" onClick={() => testInflux.mutate(form)} disabled={testInflux.isPending} data-testid="settings-influx-test-button">
            {testInflux.isPending ? "Teste…" : t("Verbindung testen")}
          </Button>
          <TestBox result={influxResult} testid="settings-influx-test-result" />
        </Panel>

        <Panel title={t("Proxmox LXC Installationsanleitung")} icon={Server} testid="settings-lxc-panel">
          <LxcGuide />
        </Panel>
      </div>

      <div className="sticky bottom-4 z-10 flex justify-end xl:col-span-2">
        <Button size="lg" className="shadow-[0_0_25px_rgba(37,99,235,0.45)]" onClick={() => save.mutate(form)} disabled={save.isPending} data-testid="settings-save-button">
          <Save className="size-4" /> {save.isPending ? "Speichert…" : t("Einstellungen speichern")}
        </Button>
      </div>
    </div>
  );
}

export default function System() {
  const settings = useSettings();
  return (
    <>
      <section className="space-y-1">
        <p className="text-sm font-medium text-[var(--primary)]">{t("Einstellungen &amp; LXC")}</p>
        <h1 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl" data-testid="system-title">{t("System &amp; Verbindungen")}</h1>
        <p className="max-w-2xl text-sm text-[#8EA8C3]">{t("Neue Verbindungen und Messpunkte unter „Datenerfassung“ anlegen. Hier Anlagenname, Zeitzone, Recorder und optionale bestehende InfluxDB-Historie konfigurieren.")}</p>
      </section>
      {settings.data && !settings.isError ? (
        <SettingsForm initial={settings.data} />
      ) : (
        <div className="space-y-6">
          <div className="text-sm text-[#8EA8C3]">{settings.isError ? t("Einstellungen derzeit nicht erreichbar.") : t("Lade Einstellungen…")}</div>
          <Panel title={t("Proxmox LXC Installationsanleitung")} icon={Server} testid="settings-lxc-panel-fallback">
            <LxcGuide />
          </Panel>
        </div>
      )}
    </>
  );
}
