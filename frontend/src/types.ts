export interface ShiftInfo {
  shift_code: string;
  shift_name: string;
  hours: number;
  station: string | null;
}

export interface EmployeeSchedule {
  employee_id: string;
  employee_name: string;
  employee_type: string;
  is_manager: boolean;
  primary_station: string;
  shifts: Record<string, ShiftInfo>;
  total_hours: number;
}

export interface Conflict {
  type: string;
  severity: string;
  description: string;
  employee_id?: string;
  days?: string[];
}

export interface WorkflowStep {
  timestamp: string;
  step: string;
  message: string;
}

export interface DailyCoverageMetrics {
  is_weekend: boolean;
  lunch_peak_met: boolean;
  dinner_peak_met: boolean;
  opening_covered: boolean;
  closing_covered: boolean;
  lunch_actual: number;
  lunch_required: number;
  dinner_actual: number;
  dinner_required: number;
  opening_actual: number;
  opening_required: number;
  closing_actual: number;
  closing_required: number;
}

export interface PeakCoverageMetrics {
  lunch_peak_met_all_days: boolean;
  dinner_peak_met_all_days: boolean;
  opening_covered_all_days: boolean;
  closing_covered_all_days: boolean;
  weekend_vs_weekday_increase: number;
  weekend_target: number;
  meets_weekend_target: boolean;
  daily_coverage: Record<string, DailyCoverageMetrics>;
}

export interface RosterResponse {
  status: string;
  roster: EmployeeSchedule[];
  days: string[];
  total_employees: number;
  generation_time_seconds: number;
  workflow_log: WorkflowStep[];
  conflicts: Conflict[];
  warnings: Conflict[];
  peak_coverage?: PeakCoverageMetrics;
  demand_analysis?: Record<string, unknown>;
  skill_matching?: Record<string, unknown>;
}

export interface AgentState {
  name: string;
  status: string;
  last_action: string | null;
  context: Record<string, unknown>;
}

export interface AgentsResponse {
  orchestrator: AgentState;
  demand: AgentState;
  matcher: AgentState;
  validator: AgentState;
  resolver: AgentState;
}
