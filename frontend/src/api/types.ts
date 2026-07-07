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
  contribution_pp: number;
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
