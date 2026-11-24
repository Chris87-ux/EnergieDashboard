import CycleSettingsEditor from "@/components/CycleSettingsEditor";
import { t } from "@/lib/i18n";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, apiGet, apiPost, apiPut } from "@/lib/api";
import { CATEGORY_LABELS } from "@/lib/format";
import { ICONS } from "@/lib/icons";
import { PHASES, type Category, type Datapoints, type Flow, type FlowInput, type Measurement, type ConsumerGroup, type Phase, type PhaseMode } from "@/lib/types";
import { cn } from "@/lib/utils";

const COLORS = ["#EAB308", "#EF4444", "#10B981", "#0EA5E9", "#38BDF8", "#F97316", "#8B5CF6", "#06B6D4", "#6366F1", "#EC4899", "#84CC16", "#F0F4F8"];

const EMPTY_DP: Datapoints = {
  power_total: "", power_l1: "", power_l2: "", power_l3: "",
  energy_total: "", energy_l1: "", energy_l2: "", energy_l3: "", frequency: "", run: "", soc: "",
};

export function emptyFlow(): FlowInput {
  return {
    name: "", category: "consumer", direction: "out", icon: "plug", color: "#38BDF8", enabled: true, sort_order: 100,
    fuel_unit: "L/h",
    capacity_kwh: null, reserve_soc_pct: 0, max_power_w: 5000, electrical_side: "ac",
    hybrid_ac_mode: "net", dc_power_unit: "W", dc_invert: false, dc_balance_complete: false, hybrid_min_power_w: 100,
    pv_type: "wr", hybrid_id: null, storage_ids: [], mppt_ids: [], dc_load_ids: [], grid_mode: "directional",
    kind: "device", parent_id: null, group_id:null, run_power_w: null, charge_sign: "negative",
    power_phase_mode: "single", power_phase: "L1", energy_phase_mode: "single", energy_phase: "L1",
    power_unit: "W", energy_unit: "kWh", invert: false, datapoints: { ...EMPTY_DP }, extra: {},
  };
}

export function toInput(f: Flow): FlowInput {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { id: _id, schema_version: _v, created_at: _c, ...rest } = f;
  return { ...rest, ...(f.category === "pv" && (f.pv_type === "mppt" || f.pv_type === "hybrid") ? {run_power_w:null} : {}), datapoints: { ...EMPTY_DP, ...f.datapoints }, extra: f.extra ?? {} };
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs font-medium text-[#8EA8C3]">{label}</Label>
      {children}
      {hint && <p className="text-[11px] leading-snug text-[#8EA8C3]/80">{hint}</p>}
    </div>
  );
}

function Segmented<T extends string>({ value, options, onChange, testid }: { value: T; options: { value: T; label: string }[]; onChange: (v: T) => void; testid: string }) {
  return (
    <div className="inline-flex rounded-lg border border-[var(--border)] bg-[var(--background)] p-0.5" data-testid={testid}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          data-testid={`${testid}-${o.value}`}
          onClick={() => onChange(o.value)}
          className={cn(
            "rounded-md px-3 py-1.5 text-xs font-semibold transition-colors duration-150",
            value === o.value ? "bg-[var(--primary)] text-white" : "text-[#8EA8C3] hover:text-white",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

const PHASE_MODE_OPTS: { value: PhaseMode; label: string }[] = [
  { value: "single", label: t("Einphasig") },
  { value: "three", label: t("Dreiphasig") },
];
const PHASE_OPTS: { value: Phase; label: string }[] = PHASES.map((p) => ({ value: p, label: p }));

interface Props {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  editing: Flow | null;
  initial: FlowInput;
  flows: Flow[];
}

export default function FlowEditor({ open, onOpenChange, editing, initial, flows }: Props) {
  const qc = useQueryClient();
  const points = useQuery({queryKey: ["measurements"], queryFn: () => apiGet<Measurement[]>("/measurements")});
  const [iconSearch, setIconSearch] = useState("");
  const [form, setForm] = useState<FlowInput>(initial);
  const [extraText, setExtraText] = useState(() => JSON.stringify(initial.extra ?? {}, null, 2));
  const set = <K extends keyof FlowInput>(k: K, v: FlowInput[K]) => setForm((f) => ({ ...f, [k]: v }));
  const setDp = (k: string, v: string) => setForm((f) => {
    const p = (points.data ?? []).find(p => "point:" + p.id === v);
    return { ...f, dc_power_unit: (k === "dc_power" || k === "dc_load_power") && (p?.unit === "W" || p?.unit === "kW") ? p.unit : f.dc_power_unit, name: f.name || p?.name.slice(0,60) || "",
      power_unit: (k.startsWith("power") || k === "ac_input") && (p?.unit === "W" || p?.unit === "kW") ? p.unit : f.power_unit,
      energy_unit: k.startsWith("energy") && (p?.unit === "Wh" || p?.unit === "kWh") ? p.unit : f.energy_unit,
      datapoints: { ...f.datapoints, [k]: v } };
  });

  const save = useMutation({
    mutationFn: (body: FlowInput) => (editing ? apiPut<Flow>(`/flows/${editing.id}`, body) : apiPost<Flow>("/flows", body)),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["flows"] });
      qc.invalidateQueries({ queryKey: ["live"] });
      qc.invalidateQueries({ queryKey: ["energy"] });
      toast.success(editing ? t("Fluss gespeichert") : t("Fluss angelegt"));
      onOpenChange(false);
    },
    onError: (e) => {
      const detail = e instanceof ApiError ? JSON.stringify((e.body as { detail?: unknown })?.detail ?? "") : String(e);
      toast.error(t("Speichern fehlgeschlagen: {0}", detail));
    },
  });

  const submit = () => {
    if (!form.name.trim()) {
      toast.error(t("Bitte einen Anzeigenamen angeben"));
      return;
    }
    let extra: Record<string, unknown>;
    try {
      const parsed: unknown = JSON.parse(extraText || "{}");
      if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) throw new Error(t("Objekt erwartet"));
      extra = parsed as Record<string, unknown>;
    } catch {
      toast.error(t("Zusätzliche Felder: ungültiges JSON-Objekt"));
      return;
    }
    if (form.kind === "storage" && (!form.capacity_kwh || form.capacity_kwh <= 0)) { toast.error(t("Bitte die Gesamtkapazität in kWh angeben")); return; }
    if (form.pv_type === "hybrid" && form.category === "pv" && !form.storage_ids.length) { toast.error(t("Bitte mindestens einen DC-Speicher auswählen")); return; }
    save.mutate({ ...form, name: form.name.trim(), extra });
  };

  const isMppt = form.kind === "device" && form.category === "pv" && form.pv_type === "mppt";
  const isHybrid = form.kind === "device" && form.category === "pv" && form.pv_type === "hybrid";
  const dcOnly = form.electrical_side === "dc";
  const singlePower = dcOnly || form.power_phase_mode === "single";
  const singleEnergy = dcOnly || form.energy_phase_mode === "single";
  const groups=useQuery({queryKey:["consumer-groups"],queryFn:()=>apiGet<ConsumerGroup[]>("/consumer-groups")});
  const nodes = flows.filter((flow) => flow.kind === "node" && flow.id !== editing?.id);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92vh] overflow-y-auto border-[var(--border)] bg-[var(--card)] sm:max-w-2xl" data-testid="flow-editor-dialog">
        <DialogHeader>
          <DialogTitle className="font-heading">{editing ? t("Gerät / Komponente bearbeiten") : t("Gerät / Komponente hinzufügen")}</DialogTitle>
          <DialogDescription>{t("Typ, Anschluss und Messpunkte festlegen.")}</DialogDescription>
        </DialogHeader>
        <Tabs defaultValue="general">
          <TabsList className="flex h-auto w-full flex-wrap">
            <TabsTrigger value="general" data-testid="flow-editor-tab-general">{t("Allgemein")}</TabsTrigger>
            <TabsTrigger value="phases" data-testid="flow-editor-tab-phases">{dcOnly ? t("DC / Energie") : t("Phasen")}</TabsTrigger>
            <TabsTrigger value="datapoints" data-testid="flow-editor-tab-datapoints">{t("Datenpunkte")}</TabsTrigger>
            {form.kind==="device"&&form.direction==="out"&&!isHybrid&&!isMppt&&<TabsTrigger value="cycles" data-testid="flow-editor-tab-cycles">{t("Gerätezyklen")}</TabsTrigger>}
            <TabsTrigger value="extra" data-testid="flow-editor-tab-extra">{t("Erweitert")}</TabsTrigger>
          </TabsList>

          <TabsContent value="general" className="mt-4 space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={t("Typ")}>
                <Select value={form.kind} onValueChange={(kind: FlowInput["kind"]) => setForm((f) => ({
                  ...f, kind, cycle_tracking: f.cycle_tracking ? {...f.cycle_tracking, enabled:false}:undefined, group_id:kind==="device"?f.group_id:null, parent_id: kind === "grid" ? null : f.parent_id, grid_mode: kind === "grid" ? "signed" : f.grid_mode, pv_type: "wr", storage_ids: [], mppt_ids: [], dc_load_ids: [],
                  run_power_w: null, datapoints: { ...f.datapoints, run: "" },
                  category: ["grid","storage","node"].includes(kind) ? "custom" : ["grid","battery"].includes(f.category) ? "consumer" : f.category,
                  electrical_side: kind === "storage" ? "dc" : "ac",
                  icon: kind === "grid" ? "utility-pole" : kind === "storage" ? "battery-full" : kind === "node" ? "network" : f.icon,
                  power_phase_mode: kind === "storage" ? "single" : f.power_phase_mode,
                }))}>
                  <SelectTrigger data-testid="flow-editor-kind"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="device">{t("Gerät / Erzeuger")}</SelectItem>
                    <SelectItem value="grid">{t("Netzanschluss")}</SelectItem>
                    <SelectItem value="node">{t("Knoten / Abschnittszähler")}</SelectItem>
                    <SelectItem value="storage">{t("Speicher")}</SelectItem>
                  </SelectContent>
                </Select>
              </Field>
              {form.kind !== "grid" && (
                <Field label={t("Anschluss")}>
                  <Select value={form.parent_id ?? "root"} onValueChange={(id) => set("parent_id", id === "root" ? null : id)}>
                    <SelectTrigger data-testid="flow-editor-parent"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="root">{t("Hauptebene / vor Abschnittszählern")}</SelectItem>
                      {nodes.map((node) => <SelectItem key={node.id} value={node.id}>{node.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </Field>
              )}
            </div>
            {form.kind === "node" && <p className="text-xs text-muted-foreground">{t("Verbraucher, Erzeuger und Speicher können an diesem Knoten hängen. Positiver Zählerwert bedeutet Verbrauch, negativer Wert Erzeugung. Ein automatischer Rest gleicht Zähler und Kinder ab. Unterknoten sind möglich.")}</p>}
            {form.kind === "storage" && (
              <Field label={t("Laden bei")}>
                <Segmented value={form.charge_sign} onChange={(v) => set("charge_sign", v)} testid="flow-editor-charge-sign"
                  options={[{ value: "negative", label: t("Negativer Leistung") }, { value: "positive", label: t("Positiver Leistung") }]} />
              </Field>
            )}
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label={t("Anzeigename")}>
                <Input value={form.name} onChange={(e) => set("name", e.target.value)} placeholder={t("z. B. Wärmepumpe")} data-testid="flow-editor-name-input" />
              </Field>
              {(form.kind === "device" && !isMppt && !isHybrid || form.kind === "grid" && form.grid_mode === "directional") && <Field label={t("Richtung")} hint={t("Geräte: Produktion oder Verbrauch. Netzbezug und Lieferung werden separat bilanziert.")}>
                <Segmented
                  value={form.direction}
                  onChange={(v) => setForm(f=>({...f,direction:v,cycle_tracking:f.cycle_tracking?{...f.cycle_tracking,enabled:v==="out"&&f.cycle_tracking.enabled}:undefined,group_id:v==="out"?f.group_id:null}))}
                  testid="flow-editor-direction"
                  options={[{ value: "in", label: form.kind === "grid" ? t("Bezug") : t("Produktion") }, { value: "out", label: form.kind === "grid" ? t("Lieferung") : t("Verbrauch") }]}
                />
              </Field>
              }
              {form.kind === "device" && <Field label={t("Kategorie")}>
                <Select value={form.category} onValueChange={(v: string) => setForm(f=>({...f,category:v as Category,cycle_tracking:f.cycle_tracking?{...f.cycle_tracking,enabled:v!=="generator"&&f.cycle_tracking.enabled}:undefined,icon:v === "generator" ? "generator" : f.icon,direction:v === "generator" ? "in" : f.direction,pv_type:v === "pv" ? f.pv_type : "wr",storage_ids:v === "pv" ? f.storage_ids : [],mppt_ids:v === "pv" ? f.mppt_ids : [],dc_load_ids:v === "pv" ? f.dc_load_ids : []}))}>
                  <SelectTrigger className="w-full" data-testid="flow-editor-category-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(Object.keys(CATEGORY_LABELS) as Category[]).filter(c => c !== "grid" && c !== "battery").map((c) => (
                      <SelectItem key={c} value={c} data-testid={`flow-editor-category-${c}`}>{CATEGORY_LABELS[c]}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Field>
              }
              <Field label={t("Anzeigereihenfolge")} hint={t("Kleinere Zahlen stehen zuerst. Gleiche Zahlen behalten ihre bisherige Reihenfolge. Keine Auswirkung auf die Bilanz.")}>
                <Input type="number" value={form.sort_order} onChange={(e) => set("sort_order", Number(e.target.value) || 0)} data-testid="flow-editor-sort-input" />
              </Field>
            </div>
            {form.kind === "storage" && <div className="grid gap-3 sm:grid-cols-3">
              <Field label={t("Gesamtkapazität (kWh)")}><Input type="number" min="0.01" step="0.1" value={form.capacity_kwh ?? ""} onChange={e => set("capacity_kwh", e.target.value ? Number(e.target.value) : null)} /></Field>
              <Field label={t("Feste SOC-Reserve (%)")} hint={t("Ersatzwert, solange kein Reserve-Datenpunkt zugeordnet ist.")}><Input type="number" min="0" max="100" value={form.reserve_soc_pct} onChange={e => set("reserve_soc_pct", Number(e.target.value))} /></Field>
              <Field label={t("Balkenmaximum (W)")}><Input type="number" min="1" value={form.max_power_w} onChange={e => set("max_power_w", Number(e.target.value))} /></Field>
            </div>}
            {form.kind === "grid" && <Field label={t("Netzmessung")}>
              <Segmented value={form.grid_mode} onChange={v => set("grid_mode", v)} testid="grid-mode" options={[{value:"signed", label:t("Ein Wert: Bezug + / Einspeisung −")},{value:"directional",label:t("Getrennter Richtungswert")}]} />
            </Field>}
            {form.kind === "device" && form.category === "pv" && <>
              <Field label={t("Photovoltaik-Typ")}><Segmented value={form.pv_type} onChange={v => setForm(f => ({...f, pv_type:v, cycle_tracking:f.cycle_tracking?{...f.cycle_tracking,enabled:false}:undefined, group_id:null, electrical_side:v === "mppt" ? "dc" : "ac", run_power_w:null, datapoints:{...f.datapoints,run:""}, power_phase_mode:v === "mppt" ? "single" : f.power_phase_mode, energy_phase_mode:v === "mppt" ? "single" : f.energy_phase_mode, direction:"in", storage_ids:v === "hybrid" ? f.storage_ids : [], mppt_ids:v === "hybrid" ? f.mppt_ids : [],dc_load_ids:v === "hybrid" ? f.dc_load_ids : []}))} testid="pv-type" options={[{value:"wr",label:t("WR")},{value:"hybrid",label:t("Hybrid-WR")},{value:"mppt",label:"DC-MPPT"}]} /></Field>
              {form.pv_type === "hybrid" && <div className="space-y-3 rounded-lg border border-border p-3">
                <p className="text-xs text-muted-foreground">{t("AC-Leistung des Hybrid-WR oben zuordnen. Speicher und MPPT zuerst anlegen und hier auswählen. DC-Werte bleiben separat.")}</p>
                {(["storage", "mppt"] as const).map(kind => <Field key={kind} label={kind === "storage" ? t("DC-Speicher") : "DC-MPPTs"}>
                  {flows.filter(f => kind === "storage" ? f.kind === "storage" && f.electrical_side === "dc" : f.kind === "device" && f.category === "pv" && f.pv_type === "mppt").map(f => {
                    const key = kind === "storage" ? "storage_ids" : "mppt_ids";
                    return <label key={f.id} className="flex gap-2 text-sm"><Checkbox checked={form[key].includes(f.id)} onCheckedChange={on => set(key, on ? [...form[key],f.id] : form[key].filter(id => id !== f.id))} />{f.name}</label>;
                  })}
                </Field>)}
                <Field label={t("DC-Verbraucher")}>
                  <p className="text-xs text-muted-foreground">{t("Einzelgeräte am DC-Bus auswählen. Alternativ den Sammelmesswert unter Datenpunkte verwenden, nicht beides zusammen.")}</p>
                  {flows.filter(f=>f.kind==="device"&&f.electrical_side==="dc"&&f.direction==="out"&&f.pv_type!=="hybrid"&&f.pv_type!=="mppt").map(f=><label key={f.id} className="flex gap-2 text-sm"><Checkbox checked={(form.dc_load_ids??[]).includes(f.id)} onCheckedChange={on=>set("dc_load_ids",on?[...(form.dc_load_ids??[]),f.id]:(form.dc_load_ids??[]).filter(id=>id!==f.id))}/>{f.name}</label>)}
                </Field>
                <Field label={t("AC-Messung")}><Segmented value={form.hybrid_ac_mode} onChange={v=>set("hybrid_ac_mode",v)} testid="hybrid-ac-mode" options={[{value:"net",label:t("WR-Nettoleistung")},{value:"terminals",label:"AC-Out minus AC-In"}]}/></Field>
                <p className="text-xs text-muted-foreground">{t("AC-Out kann Netz-Durchleitung enthalten. Im zweiten Modus den tatsächlichen WR-AC-Eingang zusätzlich zuordnen.")}</p>
                <label className="flex items-start gap-2 text-sm"><Checkbox checked={form.dc_balance_complete} onCheckedChange={v=>set("dc_balance_complete",v===true)} data-testid="hybrid-dc-balance-complete"/>{t("DC-Bilanz vollständig: alle MPPTs, DC-Speicher und weiteren DC-Lasten berücksichtigt.")}</label>
                <p className="text-xs text-muted-foreground">{t("Bestätigung aktiviert eine Wirkungsgrad-Schätzung. Eine direkte DC-Leistung am WR hat Vorrang. Unvollständige oder widersprüchliche Werte ergeben keinen Wirkungsgrad.")}</p>
                <Field label={t("Mindestleistung für Wirkungsgrad (W)")}><Input type="number" min="1" value={form.hybrid_min_power_w} onChange={e=>set("hybrid_min_power_w",Number(e.target.value))}/></Field>
              </div>}
            </>}
            {!isMppt && !isHybrid && <Field label={t("Messebene")}><Segmented value={form.electrical_side} onChange={v => setForm(f=>({...f,electrical_side:v,power_phase_mode:v === "dc" ? "single" : f.power_phase_mode}))} testid="electrical-side" options={[{value:"ac",label:"AC"},{value:"dc",label:t("DC (separate Anzeige)")}]} /></Field>}
            {form.kind==="device"&&form.direction==="out"&&!isHybrid&&<Field label={t("Zusätzliche Verbrauchergruppe (optional)")}><select className="w-full rounded-md border border-border bg-background p-2 text-sm" data-testid="flow-editor-consumer-group" value={form.group_id??""} onChange={e=>set("group_id",e.target.value||null)}><option value="">{t("Keine Gruppe")}</option>{groups.data?.map(g=><option key={g.id} value={g.id}>{g.name}</option>)}</select><p className="text-xs text-muted-foreground">{t("Gruppen vorher unter Konfiguration anlegen. Der Knotenanschluss bleibt unabhängig.")}</p></Field>}
            <Field label={t("Symbol")}>
              <Input placeholder={t("Symbole suchen")} value={iconSearch} onChange={e => setIconSearch(e.target.value)} />
              <div className="grid grid-cols-7 gap-1.5 sm:grid-cols-9" data-testid="flow-editor-icon-grid">
                {Object.entries(ICONS).filter(([key, item]) => (key + item.label).toLowerCase().includes(iconSearch.toLowerCase())).map(([key, { icon: Icon, label }]) => (
                  <button
                    key={key}
                    type="button"
                    title={label}
                    data-testid={`flow-editor-icon-${key}`}
                    onClick={() => set("icon", key)}
                    className={cn(
                      "grid aspect-square place-items-center rounded-lg border transition-colors duration-150",
                      form.icon === key ? "border-[var(--primary)] bg-accent" : "border-[var(--border)] bg-[var(--background)] hover:border-[var(--primary)]/60",
                    )}
                  >
                    <Icon className="size-4" style={{ color: form.icon === key ? form.color : "#8EA8C3" }} />
                  </button>
                ))}
              </div>
            </Field>
            <Field label={t("Farbe")}>
              <div className="flex flex-wrap items-center gap-2">
                {COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    aria-label={c}
                    data-testid={`flow-editor-color-${c.slice(1)}`}
                    onClick={() => set("color", c)}
                    className={cn("size-7 rounded-full border-2 transition-transform duration-150 hover:scale-110", form.color === c ? "border-white" : "border-transparent")}
                    style={{ background: c }}
                  />
                ))}
                <Input
                  type="color"
                  value={form.color}
                  onChange={(e) => set("color", e.target.value.toUpperCase())}
                  className="h-8 w-14 cursor-pointer p-1"
                  data-testid="flow-editor-color-input"
                />
              </div>
            </Field>
            <label className="flex items-center gap-2 text-sm">
              <Checkbox checked={form.enabled} onCheckedChange={(c) => set("enabled", c === true)} data-testid="flow-editor-enabled-checkbox" />
              {t("Fluss aktiv (im Dashboard und in der Bilanz anzeigen)")}</label>
          </TabsContent>

          <TabsContent value="phases" className="mt-4 space-y-5">
            <div className="space-y-3 rounded-lg border border-[var(--border)] bg-[var(--card)] p-4">
              <div className="font-heading text-sm font-semibold">{t("Last / Wirkleistung")}</div><p className="text-xs text-muted-foreground">{t("Dreiphasig: Gesamtleistung zählt für das ganze Gerät. Fehlende Phasen werden symmetrisch berechnet und als berechnet markiert. Einzelne Phasenmessung ohne Gesamtwert wird auf drei Phasen hochgerechnet.")}</p>
              {!dcOnly && <>
              <div className="flex flex-wrap items-center gap-3">
                <Segmented value={form.power_phase_mode} onChange={(v) => set("power_phase_mode", v)} testid="flow-editor-power-mode" options={PHASE_MODE_OPTS} />
                {singlePower && (
                  <Segmented value={form.power_phase} onChange={(v) => set("power_phase", v)} testid="flow-editor-power-phase" options={PHASE_OPTS} />
                )}
              </div>
              </>}
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label={t("Einheit Leistung")}>
                  <Segmented value={form.power_unit} onChange={(v) => set("power_unit", v)} testid="flow-editor-power-unit" options={[{ value: "W", label: "W" }, { value: "kW", label: "kW" }]} />
                </Field>
                {form.kind !== "storage" && form.run_power_w === null && <label className="flex items-center gap-2 self-end pb-1 text-sm">
                  <Checkbox checked={form.invert} onCheckedChange={(c) => set("invert", c === true)} data-testid="flow-editor-invert-checkbox" />
                  {t("Vorzeichen umkehren")}</label>}
              </div>
            </div>
            {(form.kind === "device" || form.kind === "grid") && form.run_power_w === null && <div className="space-y-3 rounded-lg border border-[var(--border)] bg-[var(--card)] p-4">
              <div className="font-heading text-sm font-semibold">{t("Zählung / Energie")}</div>
              {!dcOnly && <div className="flex flex-wrap items-center gap-3">
                <Segmented value={form.energy_phase_mode} onChange={(v) => set("energy_phase_mode", v)} testid="flow-editor-energy-mode" options={PHASE_MODE_OPTS} />
                {singleEnergy && !dcOnly && (
                  <Segmented value={form.energy_phase} onChange={(v) => set("energy_phase", v)} testid="flow-editor-energy-phase" options={PHASE_OPTS} />
                )}
              </div>}
              <Field label={t("Einheit Zählerstand")}>
                <Segmented value={form.energy_unit} onChange={(v) => set("energy_unit", v)} testid="flow-editor-energy-unit" options={[{ value: "Wh", label: "Wh" }, { value: "kWh", label: "kWh" }]} />
              </Field>
              <p className="text-[11px] text-[#8EA8C3]">
                {t("Reihenfolge der Berechnung: Zählerdelta (mit Reset-Erkennung) → Phasensumme → Integration der Wirkleistung. Fehlen Daten, wird „Nicht verfügbar“ angezeigt.")}</p>
            </div>}
          </TabsContent>

          <TabsContent value="datapoints" className="mt-4 space-y-4">
            {form.kind === "device" && !isMppt && !isHybrid && (
              <label className="flex gap-2 items-center text-sm">
                <Checkbox checked={form.run_power_w !== null} data-testid="flow-editor-run-mode"
                  onCheckedChange={(enabled) => setForm((f) => ({
                    ...f, run_power_w: enabled === true ? 100 : null,
                    power_phase_mode: f.power_phase_mode,
                    energy_phase_mode: enabled === true ? "single" : f.energy_phase_mode,
                    datapoints: { ...f.datapoints, run: enabled === true ? f.datapoints.run ?? "" : "" },
                  }))} />
                {t("Leistung aus RUN-Signal schätzen")}</label>
            )}
            {form.kind === "device" && form.run_power_w !== null && (
              <div className="grid gap-3 sm:grid-cols-2">
                <Field label={t("RUN-Datenpunkt")} hint={t("true oder ein Wert ungleich 0 bedeutet Betrieb. false oder 0 bedeutet aus.")}>
                  <Input list="measurement-options" value={form.datapoints.run ?? ""} onChange={(e) => setDp("run", e.target.value)} data-testid="flow-editor-dp-run" />
                </Field>
                <Field label={t("Leistung im Betrieb (W)")} hint={t("Die aufgezeichnete Laufzeit geht als geschätzte kWh in die Bilanz ein.")}>
                  <Input type="number" min={0.1} value={form.run_power_w} onChange={(e) => set("run_power_w", Number(e.target.value))} data-testid="flow-editor-run-watts" />
                </Field>
              </div>
            )}
            {form.kind === "storage" && (
              <><Field label={t("SOC-Datenpunkt (%)")}>
                <Input list="measurement-options" value={form.datapoints.soc ?? ""} onChange={(e) => setDp("soc", e.target.value)} data-testid="flow-editor-dp-soc" />
              </Field><Field label={t("SOC-Reserve-Datenpunkt (%)")} hint={t("Optional. Bei fehlendem/ungültigem Reservewert ist die Laufzeit unbekannt.")}><Input list="measurement-options" value={form.datapoints.soc_reserve ?? ""} onChange={e=>setDp("soc_reserve",e.target.value)} data-testid="flow-editor-dp-soc_reserve" /></Field></>
            )}
            {form.kind === "device" && form.category === "generator" && <div className="grid gap-3 sm:grid-cols-2">
              {Object.entries({engine_temperature:t("Motortemperatur (°C)"),efficiency:t("Effizienz (%)"),fuel_consumption:t("Kraftstoffverbrauch"),operating_hours:t("Betriebsstunden (h)")}).map(([key,label])=><Field key={key} label={label}><Input list="measurement-options" value={form.datapoints[key]??""} onChange={e=>setDp(key,e.target.value)} data-testid={`flow-editor-dp-${key}`} /></Field>)}
              <Field label={t("Einheit Kraftstoffverbrauch")}><select className="w-full rounded border border-border bg-background p-2" value={form.fuel_unit} onChange={e=>set("fuel_unit",e.target.value as FlowInput["fuel_unit"])}>{["L/h","L","m³/h","m³","kg/h","kg"].map(u=><option key={u}>{u}</option>)}</select></Field>
              <p className="text-xs text-muted-foreground">{t("Optionale Messwerte, keine automatische Berechnung. Effizienz in Prozent und Betriebsstunden in Stunden bereitstellen.")}</p>
            </div>}
            {isHybrid && <div className="grid gap-3 sm:grid-cols-2 rounded-lg border border-border p-3">
              {form.hybrid_ac_mode === "terminals" && <Field label={t("AC-In Gesamtleistung")} hint={t("Positiv: vom Netz in den WR. Ein-/Ausgangswerte mit derselben AC-Einheit bereitstellen.")}><Input list="measurement-options" value={form.datapoints.ac_input??""} onChange={e=>setDp("ac_input",e.target.value)} data-testid="flow-editor-dp-ac_input" /></Field>}
              <Field label={t("DC-Leistung direkt am WR (optional)")} hint={t("Positiv DC → AC, negativ AC → DC. Keine Batterie- oder MPPT-Leistung an dieser Stelle.")}><Input list="measurement-options" value={form.datapoints.dc_power??""} onChange={e=>setDp("dc_power",e.target.value)} data-testid="flow-editor-dp-dc_power" /></Field>
              <Field label={t("Weitere DC-Lasten (optional)")}><Input list="measurement-options" value={form.datapoints.dc_load_power??""} onChange={e=>setDp("dc_load_power",e.target.value)} data-testid="flow-editor-dp-dc_load_power" /></Field>
              <Field label={t("Einheit DC-Leistung")}><Segmented value={form.dc_power_unit} onChange={v=>set("dc_power_unit",v)} testid="hybrid-dc-unit" options={[{value:"W",label:"W"},{value:"kW",label:"kW"}]} /></Field>
              <label className="flex gap-2 text-sm"><Checkbox checked={form.dc_invert} onCheckedChange={v=>set("dc_invert",v===true)}/>{t("Vorzeichen der direkten DC-WR-Leistung umkehren")}</label>
            </div>}
            <datalist id="measurement-options">{(points.data ?? []).filter(p => p.enabled).map(p => <option key={p.id} value={"point:" + p.id}>{p.name} · {p.unit}</option>)}</datalist>
            <p className="text-xs text-[#8EA8C3]">{t("Messpunkt aus Datenerfassung auswählen oder bestehende ioBroker-ID eingeben, z. B. ")}<span className="font-mono text-[#93C5FD]">smartmeter.0.1-0:1_7_0__255.value</span>{t(". Leere Felder werden ignoriert.")}</p>
            {form.run_power_w === null && <div className="grid gap-3 sm:grid-cols-2">
              <Field label={isMppt ? t("DC-Leistung (MPPT-Ausgang / DC-Bus)") : isHybrid && form.hybrid_ac_mode === "terminals" ? t("AC-Out Gesamtleistung") : form.kind === "storage" ? t("Speicherleistung mit Vorzeichen") : singlePower ? t("Wirkleistung ({0})", form.power_phase) : t("Gesamtleistung (ganzes Gerät; ohne Phasenwerte symmetrisch / 3)")}>
                <Input list="measurement-options" className="font-mono text-xs" value={form.datapoints.power_total} onChange={(e) => setDp("power_total", e.target.value)} data-testid="flow-editor-dp-power_total" />
              </Field>
              {!singlePower &&
                PHASES.map((p) => (
                  <Field key={p} label={t("Wirkleistung {0}", p)}>
                    <Input list="measurement-options" className="font-mono text-xs" value={form.datapoints[`power_${p.toLowerCase()}`] ?? ""} onChange={(e) => setDp(`power_${p.toLowerCase()}`, e.target.value)} data-testid={`flow-editor-dp-power_${p.toLowerCase()}`} />
                  </Field>
                ))}
              {(form.kind === "device" || form.kind === "grid") && <><Field label={isMppt ? t("Gesamtenergie DC (Zählerstand)") : form.kind === "grid" && form.grid_mode === "signed" ? t("Zähler Netzbezug (optional)") : singleEnergy ? t("Energiezähler ({0})", form.energy_phase) : t("Energiezähler gesamt (optional)")}>
                <Input list="measurement-options" className="font-mono text-xs" value={form.datapoints[form.kind === "grid" && form.grid_mode === "signed" ? "energy_import" : "energy_total"] ?? ""} onChange={(e) => setDp(form.kind === "grid" && form.grid_mode === "signed" ? "energy_import" : "energy_total", e.target.value)} data-testid="flow-editor-dp-energy_total" />
              </Field>
              {form.kind === "grid" && form.grid_mode === "signed" && <Field label={t("Zähler Einspeisung (optional)")}><Input list="measurement-options" value={form.datapoints.energy_export ?? ""} onChange={e => setDp("energy_export",e.target.value)} /></Field>}
              {!singleEnergy &&
                PHASES.map((p) => (
                  <Field key={p} label={t("Energiezähler {0}", p)}>
                    <Input list="measurement-options" className="font-mono text-xs" value={form.datapoints[`energy_${p.toLowerCase()}`] ?? ""} onChange={(e) => setDp(`energy_${p.toLowerCase()}`, e.target.value)} data-testid={`flow-editor-dp-energy_${p.toLowerCase()}`} />
                  </Field>
                ))}
              {!isMppt && <Field label={t("Netzfrequenz (optional)")}>
                <Input list="measurement-options" className="font-mono text-xs" value={form.datapoints.frequency} onChange={(e) => setDp("frequency", e.target.value)} data-testid="flow-editor-dp-frequency" />
              </Field>}
              </>}
            </div>}
          </TabsContent>

          <TabsContent value="cycles" className="mt-4"><CycleSettingsEditor value={form.cycle_tracking} onChange={v=>set("cycle_tracking",v)} points={points.data??[]}/></TabsContent>
          <TabsContent value="extra" className="mt-4 space-y-2">
            <Field label={t("Zusätzliche Felder (JSON)")} hint={t("Zusatzmetadaten als JSON-Objekt, z. B. {\"manufacturer\":\"Victron\",\"notes\":\"Garage\"}. Kapazität und Berechnungen über die regulären Felder einstellen. Schema unter /api/schemas/flow; Anleitung in DATENMODELL.md.")}>
              <Textarea rows={8} className="font-mono text-xs" value={extraText} onChange={(e) => setExtraText(e.target.value)} data-testid="flow-editor-extra-textarea" />
            </Field>
          </TabsContent>
        </Tabs>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="flow-editor-cancel-button">{t("Abbrechen")}</Button>
          <Button onClick={submit} disabled={save.isPending} data-testid="flow-editor-save-button">
            {save.isPending ? "Speichert…" : t("Speichern")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
