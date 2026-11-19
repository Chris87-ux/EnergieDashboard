// Hand-written mirrors of the Pydantic models in backend/models/*.py — keep in sync.

export type Phase = "L1" | "L2" | "L3";
export type PhaseMode = "single" | "three";
export type Direction = "in" | "out";
export type Category = "pv" | "grid" | "battery" | "heatpump" | "ev" | "consumer" | "custom";

export const PHASES: Phase[] = ["L1", "L2", "L3"];

// models/flow.py — Datapoints (extra keys allowed)
export interface Datapoints {
  power_total: string;
  power_l1: string;
  power_l2: string;
  power_l3: string;
  energy_total: string;
  energy_l1: string;
  energy_l2: string;
  energy_l3: string;
  frequency: string;
  [key: string]: string;
}

// models/flow.py — FlowCreate
export interface FlowInput {
  kind: "device" | "node" | "storage";
  parent_id: string | null;
  run_power_w: number | null;
  charge_sign: "negative" | "positive";
  name: string;
  category: Category;
  direction: Direction;
  icon: string;
  color: string;
  enabled: boolean;
  sort_order: number;
  power_phase_mode: PhaseMode;
  power_phase: Phase;
  energy_phase_mode: PhaseMode;
  energy_phase: Phase;
  power_unit: "W" | "kW";
  energy_unit: "Wh" | "kWh";
  invert: boolean;
  datapoints: Datapoints;
  extra: Record<string, unknown>;
}

// models/flow.py — Flow
export interface Flow extends FlowInput {
  id: string;
  schema_version: number;
  created_at: string;
}

// models/settings.py
export interface IoBrokerSettings {
  host: string;
  port: number;
  protocol: "http" | "https";
  timeout_s: number;
}

export interface InfluxSettings {
  enabled: boolean;
  version: "v1" | "v2";
  url: string;
  database: string;
  username: string;
  password: string;
  org: string;
  bucket: string;
  token: string;
  field: string;
  timeout_s: number;
}

export interface RecorderSettings {
  enabled: boolean;
  interval_s: number;
}

export interface AppSettings {
  site_name: string;
  timezone: string;
  live_poll_s: number;
  gap_threshold_min: number;
  iobroker: IoBrokerSettings;
  influx: InfluxSettings;
  recorder: RecorderSettings;
}

export interface SettingsOut extends AppSettings {
  influx_password_set: boolean;
  influx_token_set: boolean;
}

export interface TestResult {
  ok: boolean;
  message: string;
  details: string[];
}

export interface RecorderStatus {
  state: "idle" | "disabled" | "waiting" | "recording" | "error";
  message: string;
  last_run: string | null;
  last_error: string | null;
  recorded_dps: string[];
  influx_dps: string[];
  samples_written: number;
  samples_total: number;
}

// models/energy.py
export type Method = "counter_delta" | "phase_sum" | "power_integral" | "run_estimate" | "unavailable" | "not_applicable";

export interface Gap {
  start: string;
  end: string;
}

export interface EnergyValue {
  kwh: number | null;
  method: Method;
  coverage: number;
  complete: boolean;
  gaps: Gap[];
  resets: number;
  note: string;
}

export interface FlowEnergy {
  parent_id: string | null;
  storage_id: string | null;
  flow_id: string;
  name: string;
  category: Category;
  direction: Direction;
  color: string;
  icon: string;
  energy_phase_mode: PhaseMode;
  energy_phase: Phase;
  total: EnergyValue;
  phases: Record<Phase, EnergyValue>;
}

export interface EnergyTotals {
  in_kwh: number | null;
  out_kwh: number | null;
  incomplete: boolean;
}

export interface EnergyReport {
  start: string;
  end: string;
  effective_end: string;
  start_local: string;
  end_local: string;
  timezone: string;
  mode: "live";
  step_s: number;
  gap_threshold_s: number;
  flows: FlowEnergy[];
  totals: EnergyTotals;
  errors: string[];
}

export interface RangePreset {
  key: string;
  label: string;
  start: string;
  end: string;
}

export interface LiveFlow {
  storage_id: string | null;
  parent_id: string | null;
  estimated: boolean;
  flow_id: string;
  name: string;
  category: Category;
  direction: Direction;
  color: string;
  icon: string;
  power_phase_mode: PhaseMode;
  power_phase: Phase;
  power_w: number | null;
  phases: Record<Phase, number | null>;
  frequency_hz: number | null;
  available: boolean;
}

export interface LiveSummary {
  in_w: number | null;
  out_w: number | null;
  pv_w: number | null;
  grid_import_w: number | null;
  grid_export_w: number | null;
  battery_charge_w: number | null;
  battery_discharge_w: number | null;
  consumption_w: number | null;
  house_rest_w: number | null;
  autarky_pct: number | null;
  self_consumption_pct: number | null;
}

export interface LiveReport {
  nodes: LiveNode[];
  storages: LiveStorage[];
  ts: string;
  mode: "live";
  ok: boolean;
  errors: string[];
  site_name: string;
  poll_s: number;
  frequency_hz: number | null;
  flows: LiveFlow[];
  summary: LiveSummary;
}

export interface LiveNode {
  id: string;
  name: string;
  phase_mode: PhaseMode;
  phase: Phase;
  phases: Record<Phase, number | null>;
  meter_w: number | null;
  children_w: number | null;
  difference_w: number | null;
}

export interface LiveStorage {
  id: string;
  name: string;
  parent_id: string | null;
  soc_pct: number | null;
  charge_w: number | null;
  discharge_w: number | null;
}
