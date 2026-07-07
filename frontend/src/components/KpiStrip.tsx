import type { CSSProperties } from "react";
import type { HealthResponse, PortfolioSummary } from "../api/types";
import type { ScoredBorrower } from "../types";

interface KpiStripProps {
  rows: ScoredBorrower[];
  summary: PortfolioSummary | null;
  health: HealthResponse | null;
  healthError: boolean;
}

function modelStatus(health: HealthResponse | null, healthError: boolean) {
  if (healthError || health === null) return "Backend offline";
  if (!health.model_loaded) return "Not loaded";
  return health.genai_available ? "Loaded · GenAI on" : "Loaded · GenAI off";
}

export function KpiStrip({ rows, summary, health, healthError }: KpiStripProps) {
  const total = summary?.total_exposure_cr ?? rows.reduce((s, r) => s + r.borrower.exposureCr, 0);
  const highRisk = summary?.high_risk ?? 0;
  const atRisk = summary?.exposure_at_risk_cr ?? 0;
  const monitored = summary?.n ?? rows.length;

  return (
    <div className="kpis">
      <div className="kpi" style={{ "--kc": "var(--idbi-bright)" } as CSSProperties}>
        <div className="kpi-label">Accounts monitored</div>
        <div className="kpi-value">{monitored.toLocaleString("en-IN")}</div>
        <div className="kpi-sub">live MSME book · ₹{total.toFixed(1)} Cr exposure</div>
      </div>
      <div className="kpi" style={{ "--kc": "var(--red)" } as CSSProperties}>
        <div className="kpi-label">High-risk (grade D+)</div>
        <div className="kpi-value">{highRisk}</div>
        <div className="kpi-sub">
          <span className="warn">₹{atRisk.toFixed(1)} Cr</span> exposure at risk
        </div>
      </div>
      <div className="kpi" style={{ "--kc": "var(--amber)" } as CSSProperties}>
        <div className="kpi-label">Risk-ranked book</div>
        <div className="kpi-value">
          {rows.length}
          <small>/ {monitored}</small>
        </div>
        <div className="kpi-sub">scored via /portfolio · SHAP on drill-down</div>
      </div>
      <div className="kpi" style={{ "--kc": "var(--teal)" } as CSSProperties}>
        <div className="kpi-label">Model status</div>
        <div className="kpi-value" style={{ fontSize: 18 }}>
          {modelStatus(health, healthError)}
        </div>
        <div className="kpi-sub">GET /health · reported by service</div>
      </div>
    </div>
  );
}
