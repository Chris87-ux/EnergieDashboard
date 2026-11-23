import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { Button } from "@/components/ui/button";

const STEPS: { title: string; text: string; code: string }[] = [
  {
    title: "1. Debian-LXC vorbereiten",
    text: "In Proxmox einen unprivilegierten Debian-12-LXC (amd64) mit LAN-Zugang anlegen. Für 30–50 Geräte zunächst 2 CPU-Kerne, 4 GB RAM und 32 GB Speicher einplanen. Lokale MongoDB benötigt AVX. Archiv und zugehörige SHA256SUMS desselben Release-Tags nach /root auf den Proxmox-Host kopieren und in der Host-Shell 123 durch die eigene Container-ID ersetzen.",
    code: `CTID=123
pct push "$CTID" /root/Energieboard-LXC.tar.gz /tmp/Energieboard-LXC.tar.gz
pct push "$CTID" /root/SHA256SUMS /tmp/SHA256SUMS
pct enter "$CTID"`,
  },
  {
    title: "2. Im Container installieren",
    text: "In der LXC-Konsole als root ausführen. Die Oberfläche ist im Archiv fertig gebaut. Das Skript richtet Python, lokale MongoDB und den Dienst energieboard ein. Nur für eine neue Installation. Für externe MongoDB und die direkte Installation von GitHub siehe INSTALLATION.md.",
    code: `cd /tmp
sha256sum -c SHA256SUMS && mkdir -p /opt && tar -xzf Energieboard-LXC.tar.gz -C /opt &&
bash /opt/energieboard/deploy/install.sh`,
  },
  {
    title: "3. Dienst prüfen",
    text: "Der Dienst startet beim Hochfahren des Containers. Port 8000 auf vertrauenswürdige Geräte beschränken oder einen Reverse-Proxy mit Zugriffsschutz einsetzen.",
    code: `systemctl status energieboard
journalctl -u energieboard -n 60 --no-pager`,
  },
  {
    title: "4. Datenquellen verbinden",
    text: "Im Browser die IP des LXC-Containers auf Port 8000 öffnen. Unter „Datenerfassung“ Verbindungen (ioBroker, MQTT, Modbus TCP) und Messpunkte anlegen. Unter „Konfiguration“ zuerst den Netzanschluss und danach Knoten, Geräte und Speicher einrichten. InfluxDB und Aufzeichnung stehen unter „System“.",
    code: `# Beispiel für die Adresse im Browser
http://<LXC-IP>:8000/datenerfassung`,
  },
  {
    title: "5. Aktualisieren",
    text: "Das Update sichert Anwendung, Datenbank und Konfiguration. Messpunkt-IDs und Historie bleiben erhalten. Bei einem Fehler wird die Sicherung zurückgespielt. Nur für die direkte LXC-Installation. Docker wird über Git-Tag und Compose aktualisiert. Bei späteren Releases den gewünschten festen Tag einsetzen.",
    code: `bash /opt/energieboard/deploy/update.sh v2.4.0`,
  },
];

function CodeBlock({ code, testid }: { code: string; testid: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };
  return (
    <div className="relative">
      <pre className="overflow-x-auto rounded-lg border border-[var(--border)] bg-[var(--background)] p-3 pr-12 font-mono text-[11px] leading-relaxed text-[#BFDBFE]">{code}</pre>
      <Button variant="ghost" size="icon-sm" className="absolute right-2 top-2" onClick={copy} aria-label="Kopieren" data-testid={testid}>
        {copied ? <Check className="size-4 text-[#34D399]" /> : <Copy className="size-4" />}
      </Button>
    </div>
  );
}

export default function LxcGuide() {
  return (
    <div className="space-y-5" data-testid="lxc-guide">
      <p className="text-xs text-muted-foreground">Aktuelle Schritt-für-Schritt-Anleitungen auf GitHub: <a className="underline" href="https://github.com/Chris87-ux/EnergieDashboard/blob/main/INSTALLATION.md" target="_blank" rel="noreferrer">Proxmox-LXC</a> · <a className="underline" href="https://github.com/Chris87-ux/EnergieDashboard/blob/main/DOCKER.md" target="_blank" rel="noreferrer">Docker</a> · <a className="underline" href="https://github.com/Chris87-ux/EnergieDashboard/blob/main/docs/README.md" target="_blank" rel="noreferrer">Konfiguration und Betrieb</a></p>
      <div className="grid gap-2 rounded-lg border border-[var(--border)] bg-[var(--card)] p-4 font-mono text-[11px] text-[#93C5FD] sm:grid-cols-[1fr_auto_1fr_auto_1fr] sm:items-center sm:text-center">
        <div className="rounded-md border border-[var(--border)] bg-[var(--card)] p-2">Browser im LAN</div>
        <div className="text-[#8EA8C3]">→ :8000</div>
        <div className="rounded-md border border-[var(--primary)] bg-accent p-2 text-white">LXC Energieboard<br />FastAPI · MongoDB</div>
        <div className="text-[#8EA8C3]">→</div>
        <div className="rounded-md border border-[var(--border)] bg-[var(--card)] p-2">ioBroker / MQTT / Modbus TCP<br />optional InfluxDB</div>
      </div>
      {STEPS.map((s, i) => (
        <div key={s.title} className="space-y-2">
          <div className="font-heading text-sm font-semibold">{s.title}</div>
          <p className="text-xs text-[#8EA8C3]">{s.text}</p>
          <CodeBlock code={s.code} testid={`lxc-copy-step-${i + 1}`} />
        </div>
      ))}
    </div>
  );
}
