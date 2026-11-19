import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import type { EnergyReport, Flow, LiveReport, RangePreset, RecorderStatus, SettingsOut } from "@/lib/types";

export function useLive() {
  return useQuery({
    queryKey: ["live"],
    queryFn: () => apiGet<LiveReport>("/live"),
    refetchInterval: (q) => (q.state.data?.poll_s ?? 5) * 1000,
    retry: 1,
  });
}

export function useFlows() {
  return useQuery({ queryKey: ["flows"], queryFn: () => apiGet<Flow[]>("/flows") });
}

export function useSettings() {
  return useQuery({ queryKey: ["settings"], queryFn: () => apiGet<SettingsOut>("/settings") });
}

export function usePresets() {
  return useQuery({ queryKey: ["presets"], queryFn: () => apiGet<RangePreset[]>("/energy/presets"), refetchInterval: 60000 });
}

export function useRecorder() {
  return useQuery({
    queryKey: ["recorder"],
    queryFn: () => apiGet<RecorderStatus>("/recorder/status"),
    refetchInterval: 10000,
  });
}

export interface Range {
  start: string;
  end: string;
}

export function useEnergy(range: Range | null) {
  return useQuery({
    queryKey: ["energy", range?.start, range?.end],
    queryFn: () =>
      apiGet<EnergyReport>(
        `/energy?start=${encodeURIComponent(range!.start)}&end=${encodeURIComponent(range!.end)}`,
      ),
    enabled: !!range,
    refetchInterval: (query) => {
      const end = query.state.data?.end;
      return end && Date.parse(end) >= Date.now() ? 60000 : false;
    },
    retry: false,
  });
}

export function useEnergyToday() {
  return useQuery({
    queryKey: ["energy", "preset", "today"],
    queryFn: () => apiGet<EnergyReport>("/energy?preset=today"),
    refetchInterval: 60000,
    retry: 1,
  });
}
