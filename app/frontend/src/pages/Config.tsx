import CsvConfiguration from "@/components/CsvConfiguration";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowDownLeft, ArrowUpRight, Pencil, Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";
import FlowEditor, { emptyFlow, toInput } from "@/components/FlowEditor";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { ApiError, apiDelete, apiPut } from "@/lib/api";
import { CATEGORY_LABELS } from "@/lib/format";
import { iconFor } from "@/lib/icons";
import { useFlows } from "@/lib/queries";
import type { Flow, FlowInput } from "@/lib/types";

function phaseLabel(mode: string, phase: string) {
  return mode === "three" ? "3-phasig" : `1-phasig ${phase}`;
}

function FlowRow({ flow, parentName, onEdit, onDelete, onToggle }: { flow: Flow; parentName?: string; onEdit: () => void; onDelete: () => void; onToggle: (v: boolean) => void }) {
  const Icon = iconFor(flow.icon);
  const mapped = Object.values(flow.datapoints).filter((v) => v && String(v).trim()).length;
  return (
    <div
      className="flex flex-col gap-3 rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 transition-[border-color] duration-200 hover:border-[var(--primary)]/60 sm:flex-row sm:items-center"
      data-testid={`config-flow-row-${flow.id}`}
    >
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <span className="grid size-10 shrink-0 place-items-center rounded-lg" style={{ background: `${flow.color}22` }}>
          <Icon className="size-5" style={{ color: flow.color }} />
        </span>
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="truncate font-heading font-semibold" data-testid={`config-flow-name-${flow.id}`}>{flow.name}</span>
            {!flow.enabled && <span className="rounded border border-[var(--border)] px-1.5 text-[10px] text-[#8EA8C3]">inaktiv</span>}
          </div>
          <div className="mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-[#8EA8C3]">
            <span>{flow.kind === "storage" ? "Speicher" : flow.kind === "node" ? "Knoten" : CATEGORY_LABELS[flow.category]}</span>
            <span>Last: {phaseLabel(flow.power_phase_mode, flow.power_phase)}</span>
            <span>Zählung: {phaseLabel(flow.energy_phase_mode, flow.energy_phase)}</span>
            <span>{mapped} Datenpunkt(e)</span>
            <span>{parentName ?? "Hauptebene"}</span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <label className="mr-2 flex items-center gap-1.5 text-xs text-[#8EA8C3]">
          <Checkbox checked={flow.enabled} onCheckedChange={(c) => onToggle(c === true)} data-testid={`config-flow-enabled-${flow.id}`} />
          aktiv
        </label>
        <Button variant="outline" size="sm" onClick={onEdit} data-testid={`config-flow-edit-${flow.id}`}>
          <Pencil className="size-3.5" /> Bearbeiten
        </Button>
        <Button variant="ghost" size="icon-sm" onClick={onDelete} aria-label="Löschen" data-testid={`config-flow-delete-${flow.id}`}>
          <Trash2 className="size-4 text-[#F87171]" />
        </Button>
      </div>
    </div>
  );
}

export default function Config() {
  const qc = useQueryClient();
  const flows = useFlows();
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<Flow | null>(null);
  const [initial, setInitial] = useState<FlowInput>(emptyFlow());
  const [editorKey, setEditorKey] = useState(0);
  const [toDelete, setToDelete] = useState<Flow | null>(null);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["flows"] });
    qc.invalidateQueries({ queryKey: ["live"] });
    qc.invalidateQueries({ queryKey: ["energy"] });
  };

  const del = useMutation({
    mutationFn: (id: string) => apiDelete<void>(`/flows/${id}`),
    onSuccess: () => {
      invalidate();
      toast.success("Fluss gelöscht");
      setToDelete(null);
    },
    onError: (error) => toast.error(error instanceof ApiError ? String((error.body as { detail?: unknown })?.detail ?? "Speichern fehlgeschlagen") : String(error)),
  });
  const toggle = useMutation({
    mutationFn: ({ flow, enabled }: { flow: Flow; enabled: boolean }) => apiPut<Flow>(`/flows/${flow.id}`, { ...toInput(flow), enabled }),
    onSuccess: invalidate,
    onError: (error) => toast.error(error instanceof ApiError ? String((error.body as { detail?: unknown })?.detail ?? "Speichern fehlgeschlagen") : String(error)),
  });

  const openEditor = (f: Flow | null, dir?: "in" | "out") => {
    setEditing(f);
    const base = f ? toInput(f) : emptyFlow();
    if (!f && dir) base.direction = dir;
    setInitial(base);
    setEditorKey((k) => k + 1);
    setEditorOpen(true);
  };

  const list = flows.isError ? [] : flows.data ?? [];
  function path(id:string|null,seen=new Set<string>()):string {
    if(!id)return "Haus";if(seen.has(id))return "⚠ Kreis";
    const parent=list.find(n=>n.id===id);if(!parent)return "⚠ Zuordnung fehlt";
    seen.add(id);return `${path(parent.parent_id,seen)} → ${parent.name}`;
  }
  const [search, setSearch] = useState("");
  const visible = list.filter((flow) => flow.name.toLocaleLowerCase().includes(search.toLocaleLowerCase()));
  const groups = [
    { dir: "in" as const, title: "Produktion", desc: "Lokale Erzeuger und Produktionsgeräte; Netz und Speicher separat", icon: ArrowDownLeft },
    { dir: "out" as const, title: "Verbrauch", desc: "Verbrauchsgeräte; Netzlieferung und Speicher separat", icon: ArrowUpRight },
  ];

  return (
    <>
      <section className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1">
          <p className="text-sm font-medium text-[var(--primary)]">Fluss-Konfiguration</p>
          <h1 className="font-heading text-2xl font-bold tracking-tight sm:text-3xl" data-testid="config-title">Zu- und Verbrauch</h1>
          <p className="max-w-2xl text-sm text-[#8EA8C3]">Beliebig viele Flüsse mit eigenen ioBroker-Datenpunkten, Name, Symbol, Farbe, Kategorie und Phasen-Zuordnung.</p>
        </div>
        <Button onClick={() => openEditor(null)} data-testid="add-flow-button">
          <Plus className="size-4" /> Neuer Fluss
        </Button>
      </section>

      {flows.isError && <div className="text-sm text-[#F87171]">Konfiguration konnte nicht geladen werden.</div>}

      <CsvConfiguration />
      <Input aria-label="Geräte und Knoten suchen" placeholder="Geräte, Knoten oder Speicher suchen" value={search} onChange={(e) => setSearch(e.target.value)} />
      {groups.map((g) => {
        const items = visible.filter((f) => f.kind === "device" && f.direction === g.dir);
        return (
          <section key={g.dir} className="space-y-3" data-testid={`config-group-${g.dir}`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <g.icon className="size-5 text-[var(--primary)]" />
                <h2 className="font-heading text-lg font-semibold">{g.title}</h2>
                <span className="rounded-md bg-muted px-2 py-0.5 font-mono text-xs text-[#93C5FD]">{items.length}</span>
              </div>
              <Button variant="ghost" size="sm" onClick={() => openEditor(null, g.dir)} data-testid={`config-add-${g.dir}-button`}>
                <Plus className="size-4" /> Hinzufügen
              </Button>
            </div>
            <p className="text-xs text-[#8EA8C3]">{g.desc}</p>
            <div className="space-y-2">
              {items.map((f) => (
                <FlowRow
                  key={f.id}
                  flow={f}
                  parentName={path(f.parent_id)}
                  onEdit={() => openEditor(f)}
                  onDelete={() => setToDelete(f)}
                  onToggle={(enabled) => toggle.mutate({ flow: f, enabled })}
                />
              ))}
              {items.length === 0 && !flows.isLoading && (
                <div className="rounded-xl border border-dashed border-[var(--border)] p-6 text-center text-sm text-[#8EA8C3]">Noch keine {g.title}.</div>
              )}
            </div>
          </section>
        );
      })}

      {(["grid", "node", "storage"] as const).map((kind) => (
        <section key={kind} className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-heading text-lg font-semibold">{kind === "grid" ? "Netzanschlüsse" : kind === "node" ? "Knoten" : "Speicher"}</h2>
            <Button variant="outline" data-testid={`config-add-${kind}-button`} onClick={() => {
              openEditor(null);
              setInitial({ ...emptyFlow(), kind, grid_mode: kind === "grid" ? "signed" : "directional", electrical_side: kind === "storage" ? "dc" : "ac", category: "custom", icon: kind === "grid" ? "utility-pole" : kind === "storage" ? "battery-full" : "network" });
            }}><Plus className="size-4" /> {kind === "grid" ? "Netzanschluss hinzufügen" : kind === "node" ? "Knoten hinzufügen" : "Speicher hinzufügen"}</Button>
          </div>
          {visible.filter((flow) => flow.kind === kind).map((flow) => (
            <FlowRow key={flow.id} flow={flow} parentName={path(flow.parent_id)} onEdit={() => openEditor(flow)} onDelete={() => setToDelete(flow)} onToggle={(enabled) => toggle.mutate({ flow, enabled })} />
          ))}
        </section>
      ))}
      <FlowEditor key={editorKey} open={editorOpen} onOpenChange={setEditorOpen} editing={editing} initial={initial} flows={list} />

      <Dialog open={!!toDelete} onOpenChange={(o) => !o && setToDelete(null)}>
        <DialogContent className="border-[var(--border)] bg-[var(--card)]" data-testid="delete-flow-dialog">
          <DialogHeader>
            <DialogTitle>Fluss löschen?</DialogTitle>
            <DialogDescription>„{toDelete?.name}“ wird aus Dashboard und Bilanz entfernt. Historie in InfluxDB bleibt erhalten.</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setToDelete(null)} data-testid="delete-flow-cancel">Abbrechen</Button>
            <Button variant="destructive" onClick={() => toDelete && del.mutate(toDelete.id)} data-testid="delete-flow-confirm">Löschen</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

    </>
  );
}
