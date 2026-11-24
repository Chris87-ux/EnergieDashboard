import { t, language } from "@/lib/i18n";
import { useState } from "react";
import { format, parse } from "date-fns";
import { de, enGB } from "date-fns/locale";
import type { DateRange } from "react-day-picker";
import { CalendarRange } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import type { Range } from "@/lib/queries";
import type { RangePreset } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  value: Range | null;
  presets: RangePreset[];
  onChange: (r: Range, presetKey?: string) => void;
  activePreset?: string;
}

const toDate = (local: string) => parse(local, "yyyy-MM-dd'T'HH:mm", new Date());

export default function RangePicker({ value, presets, onChange, activePreset }: Props) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<DateRange | undefined>();
  const [fromTime, setFromTime] = useState("00:00");
  const [toTime, setToTime] = useState("23:59");

  const openPicker = (o: boolean) => {
    if (o && value) {
      const a = toDate(value.start);
      const b = toDate(value.end);
      setDraft({ from: a, to: b });
      setFromTime(format(a, "HH:mm"));
      setToTime(format(b, "HH:mm"));
    }
    setOpen(o);
  };

  const apply = () => {
    if (!draft?.from) return;
    const to = draft.to ?? draft.from;
    onChange({
      start: `${format(draft.from, "yyyy-MM-dd")}T${fromTime}`,
      end: `${format(to, "yyyy-MM-dd")}T${toTime}`,
    });
    setOpen(false);
  };

  const label = value
    ? `${format(toDate(value.start), language === "en" ? "dd/MM/yyyy HH:mm" : "dd.MM.yyyy HH:mm")} – ${format(toDate(value.end), language === "en" ? "dd/MM/yyyy HH:mm" : "dd.MM.yyyy HH:mm")}`
    : t("Zeitraum wählen");

  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-center" data-testid="energy-range-picker">
      <div className="flex flex-wrap gap-1.5">
        {presets.map((p) => (
          <button
            key={p.key}
            type="button"
            data-testid={`energy-picker-preset-${p.key}`}
            onClick={() => onChange({ start: p.start, end: p.end }, p.key)}
            className={cn(
              "rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors duration-150",
              activePreset === p.key
                ? "border-[var(--primary)] bg-[var(--primary)] text-white"
                : "border-[var(--border)] bg-[var(--card)] text-[#8EA8C3] hover:border-[var(--primary)]/60 hover:text-white",
            )}
          >
            {p.label}
          </button>
        ))}
      </div>
      <Popover open={open} onOpenChange={openPicker}>
        <PopoverTrigger asChild>
          <Button variant="outline" className="h-9 justify-start gap-2 border-[var(--border)] bg-[var(--card)] font-mono text-xs sm:text-sm" data-testid="energy-picker-open-button">
            <CalendarRange className="size-4 text-[var(--primary)]" />
            <span data-testid="energy-picker-label">{label}</span>
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto border-[var(--border)] bg-[var(--card)] p-3" align="start">
          <Calendar
            mode="range"
            selected={draft}
            onSelect={setDraft}
            numberOfMonths={1}
            locale={language === "en" ? enGB : de}
            weekStartsOn={1}
            defaultMonth={draft?.from}
            data-testid="energy-picker-calendar"
          />
          <div className="mt-3 grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label htmlFor="from-time" className="text-xs text-[#8EA8C3]">{t("Von (Uhrzeit)")}</Label>
              <Input id="from-time" type="time" value={fromTime} onChange={(e) => setFromTime(e.target.value)} data-testid="energy-picker-from-time" />
            </div>
            <div className="space-y-1">
              <Label htmlFor="to-time" className="text-xs text-[#8EA8C3]">{t("Bis (Uhrzeit)")}</Label>
              <Input id="to-time" type="time" value={toTime} onChange={(e) => setToTime(e.target.value)} data-testid="energy-picker-to-time" />
            </div>
          </div>
          <Button className="mt-3 w-full" onClick={apply} disabled={!draft?.from} data-testid="energy-picker-apply-button">
            {t("Zeitraum übernehmen")}</Button>
        </PopoverContent>
      </Popover>
    </div>
  );
}
