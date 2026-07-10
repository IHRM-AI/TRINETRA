export type Grade = "A" | "B" | "C" | "D" | "E";

export type FeatureValue = number | string | null;

export type Features = Record<string, FeatureValue>;

export interface HealthResponse {
  status: string;
  model_loaded: boolean;
  genai_available: boolean;
}

export interface ReasonCode {
  code: string;
  label: string;
  contribution_logodds: number;
  direction: string;
}

export interface ScoreResponse {
  pd: number;
  grade: Grade;
  watch_tier: string;
  reason_codes: ReasonCode[];
}

export interface MemoResponse {
  borrower: string;
  body: string;
  status: string;
  generated_by: string;
  sources: string[];
}

export interface TermStructureResponse {
  months: number[];
  marginal_pd: number[];
  cumulative_pd: number[];
  peak_month: number;
}

export interface Account {
  id: string;
  name: string;
  account: string;
  sector: string;
  region: string;
  exposure_cr: number;
  pd: number;
  grade: Grade;
  watch_tier: string;
  features: Features;
}

export interface PortfolioSummary {
  n: number;
  total_exposure_cr: number;
  high_risk: number;
  exposure_at_risk_cr: number;
  synthetic?: boolean;
  note?: string;
}

export interface PortfolioResponse {
  accounts: Account[];
  summary: PortfolioSummary;
}

export interface CapturePoint {
  flag_rate: number;
  capture: number;
}

export interface BenchmarkResponse {
  default_rate: number;
  metrics: { auc: number; gini: number; ks: number };
  capture_at_20pct: { model: number; rule_baseline: number };
  capture_curve_model: CapturePoint[];
  capture_curve_rule: CapturePoint[];
}
