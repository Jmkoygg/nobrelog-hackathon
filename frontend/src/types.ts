export interface Batch {
  id: string;
  filename: string;
  mode: "simulacao_historica" | "operacao";
  status: string;
  summary: { total_linhas?: number; excluidos?: number; pendentes?: number; disponiveis?: number };
  created_at: string;
}

export interface Order {
  id: string;
  external_id: string;
  city: string;
  axis_id: string | null;
  value: number | null;
  weight_kg: number | null;
  volume_m3: number | null;
  data_status: "ready" | "pending" | "excluded";
  excluded_reason: string | null;
  delivered: boolean;
}

export interface Issue {
  id: string;
  order_id: string | null;
  product_code: string | null;
  issue_type: string;
  description: string;
  status: string;
}

export interface Vehicle {
  id: string;
  name: string;
  capacity_kg: number;
  capacity_m3: number;
  active: boolean;
  version: number;
}

export interface Axis {
  id: string;
  name: string;
  cities: City[];
}

export interface ProductSpec {
  id: string;
  code: string;
  description: string | null;
  sale_unit: string | null;
  load_unit: string | null;
  conversion_factor: number | null;
  weight_kg: number | null;
  volume_m3: number | null;
  is_estimated: boolean;
  source: string | null;
}

export interface PlanOrderRow {
  id: string;
  order_id: string;
  selected: boolean;
  rejection_reason: string | null;
  city: string;
  stop_sequence: number | null;
  value: number;
  weight_kg: number;
  volume_m3: number;
  orders?: { external_id: string; city: string };
}

export interface Plan {
  id: string;
  axis_id: string;
  vehicle_id: string;
  batch_id: string;
  mode: string;
  status: "draft" | "issued" | "cancelled" | "completed";
  objective_policy: string;
  solver_status: string;
  total_weight_kg: string;
  total_volume_m3: string;
  total_value: string;
  created_at: string;
  issued_at: string | null;
  axes?: { name: string };
  vehicles?: { name: string };
}

export interface City {
  id: string;
  name: string;
  axis_id: string | null;
  lat: number | null;
  lng: number | null;
  is_depot: boolean;
  sort_order: number;
  city_aliases: string[];
}

export interface DispatchRun {
  id: string;
  batch_id: string;
  mode: string;
  status: "draft" | "issued" | "cancelled";
  solver_status: string | null;
  total_distance_km: number | null;
  total_value: number | null;
  created_at: string;
  issued_at: string | null;
}

export interface DispatchAssignment {
  id: string;
  order_id: string;
  vehicle_id: string | null;
  city: string;
  stop_sequence: number | null;
  leg_distance_km: number | null;
  value: number;
  weight_kg: number;
  volume_m3: number;
  selected: boolean;
  rejection_reason: string | null;
  orders?: { external_id: string; city: string };
  vehicles?: { name: string } | null;
}

export interface SolveResponse {
  plan: Plan;
  solver_status: string;
  validated: boolean;
  validation_errors: string[];
  occupancy_kg_pct: number;
  occupancy_m3_pct: number;
  selected_count: number;
  candidate_count: number;
}
