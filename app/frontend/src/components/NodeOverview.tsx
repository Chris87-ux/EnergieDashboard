import { useState } from "react";
import FlowCard from "@/components/FlowCard";
import { Input } from "@/components/ui/input";
import { fmtPct, fmtW } from "@/lib/format";
import type { FlowEnergy, LiveReport, Phase } from "@/lib/types";

export default function NodeOverview({ data, energy }: { data: LiveReport; energy: FlowEnergy[] }) {
  const [search, setSearch] = useState("");
  const match = (name: string) => name.toLocaleLowerCase().includes(search.toLocaleLowerCase());
  const energyById = new Map(energy.map((flow) => [flow.flow_id, flow]));
  const groups = [
    { id: null, name: "Hauptebene" },
    ...data.nodes.map((node) => ({ id: node.id, name: node.name })),
  ];

  return (
    <section className="space-y-4">
      <h2 className="font-heading text-lg font-semibold">Produktion, Verbrauch und Speicher</h2>
      <Input aria-label="Geräte suchen" placeholder="Geräte oder Knoten suchen" value={search} onChange={(event) => setSearch(event.target.value)} />
      {groups.map((group) => {
        const node = data.nodes.find((item) => item.id === group.id);
        const children = data.flows.filter((flow) => flow.parent_id === group.id);
        const childCount = children.filter((flow) => !flow.storage_id).length + data.storages.filter((item) => item.parent_id === group.id).length;
        const visible = children.filter((flow) => match(flow.name) || match(group.name));
        const storage = data.storages.filter((item) => item.parent_id === group.id && (match(item.name) || match(group.name)));
        if (group.id === null && children.length === 0 && storage.length === 0) return null;
        if (search && visible.length === 0 && storage.length === 0 && !match(group.name)) return null;
        return (
          <div key={group.id ?? "root"} className="rounded-xl border border-border bg-card p-4" data-testid={`node-group-${group.id ?? "root"}`}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="font-heading font-semibold">{group.name}</h3>
              {node && <details className="text-sm" data-testid={`node-meter-${node.id}`}>
                <summary className="cursor-pointer text-[#BFDBFE]">Zähler und Verrechnung</summary>
                <dl className="mt-2 space-y-1 text-xs text-muted-foreground">
                  <div>Zähler netto {fmtW(node.meter_w)}</div>
                  <div>Geräte netto {fmtW(node.children_w)}</div>
                  <div>Unzugeordnete Differenz {fmtW(node.difference_w)}</div>
                  {(node.phase_mode === "three" ? ["L1", "L2", "L3"] as Phase[] : [node.phase]).map((phase) => <div key={phase}>{phase} {fmtW(node.phases[phase])}</div>)}
                  <div>Positiv = Verbrauch · negativ = Erzeugung</div>
                </dl>
              </details>}
            </div>
            {storage.map((item) => (
              <div key={item.id} className="mt-3 flex flex-wrap gap-4 rounded-lg border border-border bg-background p-3 text-sm" data-testid={`storage-${item.id}`}>
                <span className="font-semibold">{item.name}</span>
                <span>SOC {fmtPct(item.soc_pct)}</span>
                <span>Laden {fmtW(item.charge_w)}</span>
                <span>Entladen {fmtW(item.discharge_w)}</span>
              </div>
            ))}
            <details open={group.id === null || search.length > 0} className="mt-4">
              <summary className="cursor-pointer text-sm text-[#BFDBFE]">Geräte und Tageswerte ({childCount})</summary>
              <div className="mt-3 grid gap-4 lg:grid-cols-2">
              {(["in", "out"] as const).map((direction) => (
                <div key={direction} className="space-y-3">
                  <h4 className="text-sm font-semibold text-[#BFDBFE]">{direction === "in" ? "Produktion / Zufluss" : "Verbrauch / Abfluss"}</h4>
                  {visible.filter((flow) => flow.direction === direction && !flow.storage_id).map((flow) => (
                    <FlowCard key={flow.flow_id} flow={flow} energy={energyById.get(flow.flow_id)} />
                  ))}
                  {visible.filter((flow) => flow.direction === direction && flow.storage_id).map((flow) => (
                    <div key={flow.flow_id} className="flex justify-between gap-2 text-xs text-muted-foreground">
                      <span>{flow.name}</span><span>{energyById.get(flow.flow_id)?.total.kwh?.toLocaleString("de-DE", { maximumFractionDigits: 3 }) ?? "n. v."} kWh heute</span>
                    </div>
                  ))}
                </div>
              ))}
              </div>
            </details>
          </div>
        );
      })}
    </section>
  );
}
