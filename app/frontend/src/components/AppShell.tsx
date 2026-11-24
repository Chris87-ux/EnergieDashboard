import LanguageSelector from "@/components/LanguageSelector";
import { t } from "@/lib/i18n";
import { NavLink, Outlet } from "react-router-dom";
import { Database, Palette, Activity, BarChart3, Server, SlidersHorizontal, Zap } from "lucide-react";
import { Toaster } from "@/components/ui/sonner";
import { useLive } from "@/lib/queries";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: t("Energiefluss"), icon: Activity, testid: "nav-dashboard" },
  { to: "/energie", label: t("Energie-Bilanz"), icon: BarChart3, testid: "nav-energy" },
  { to: "/konfiguration", label: t("Konfiguration"), icon: SlidersHorizontal, testid: "nav-config" },
  { to: "/datenerfassung", label: t("Datenerfassung"), icon: Database, testid: "nav-acquisition" },
  { to: "/darstellung", label: t("Darstellung"), icon: Palette, testid: "nav-appearance" },
  { to: "/system", label: "System & LXC", icon: Server, testid: "nav-system" },
];

function ModeIndicator() {
  const { data, isError } = useLive();
  const offline = isError || !data;
  const label = offline ? t("Keine Verbindung") : data.ok ? "Live" : t("Live – Einrichtung prüfen");
  const color = offline || !data.ok ? "bg-[#F87171]" : "bg-[#34D399]";
  return (
    <div
      data-testid="header-mode-indicator"
      className="flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--card)] px-3 py-1.5 text-xs font-medium text-[#8EA8C3]"
    >
      <span className={cn("size-2 rounded-full animate-live-pulse", color)} />
      <span className="hidden sm:inline">{label}</span>
    </div>
  );
}

export default function AppShell() {
  return (
    <div className="flex min-h-screen flex-col bg-[var(--background)] font-sans text-[#F0F4F8]">
      <header className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--background)]/85 backdrop-blur-xl">
        <div className="mx-auto flex h-16 w-full max-w-[1600px] items-center justify-between gap-4 px-4 sm:px-8">
          <NavLink to="/" className="flex items-center gap-2.5" data-testid="header-logo">
            <span className="grid size-9 place-items-center rounded-lg bg-[var(--primary)] shadow-[0_0_25px_rgba(37,99,235,0.45)]">
              <Zap className="size-5 text-white" strokeWidth={2.4} />
            </span>
            <span className="font-heading text-lg font-bold tracking-tight">Energy Flow</span>
          </NavLink>
          <nav className="hidden items-center gap-1 xl:flex" data-testid="main-nav">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                data-testid={n.testid}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-150",
                    isActive ? "bg-accent text-white" : "text-[#8EA8C3] hover:bg-[var(--card)] hover:text-white",
                  )
                }
              >
                <n.icon className="size-4" />
                {n.label}
              </NavLink>
            ))}
          </nav>
          <div className="flex shrink-0 items-center gap-2"><LanguageSelector /><ModeIndicator /></div>
        </div>
        <nav className="flex gap-1 overflow-x-auto border-t border-[var(--border)] px-2 py-1.5 xl:hidden" data-testid="mobile-nav">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/"}
              data-testid={`mobile-${n.testid}`}
              className={({ isActive }) =>
                cn(
                  "flex shrink-0 items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors duration-150",
                  isActive ? "bg-accent text-white" : "text-[#8EA8C3]",
                )
              }
            >
              <n.icon className="size-3.5" />
              {n.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto w-full max-w-[1600px] flex-1 space-y-6 p-4 sm:space-y-8 sm:p-6 lg:p-8">
        <Outlet />
      </main>
      <footer className="border-t border-[var(--border)] px-4 py-4 text-center text-xs text-[#8EA8C3] sm:px-8">
        {t("Energy Flow · selbst gehostet für ioBroker &amp; InfluxDB")}</footer>
      <Toaster richColors />
    </div>
  );
}
