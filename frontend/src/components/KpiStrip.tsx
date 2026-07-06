import type { CSSProperties } from "react";
import type { HealthResponse } from "../api/types";
import type { ScoredBorrower } from "../types";

interface KpiStripProps {
  rows: ScoredBorrower[];
  health: HealthResponse | null;
  healthError: boolean;
}

const HIGH_RISK_PD = 0.15;

function modelStatus(health: HealthResponse | null, healthError: boolean) {
  if (healthError || health === null) return "Backend offline";
  if (!health.model_loaded) return "Not loaded";
  return health.genai_available ? "Loaded · GenAI on" : "Loaded · GenAI off";
}

export function KpiStrip({ rows, health, healthError }: KpiStripProps) {
  const scored = rows.filter((row) => row.score !== null);
  const highRisk = scored.filter(
    (row) => row.score !== null && row.score.pd >= HIGH_RISK_PD,
  );
  const highRiskExposure = highRisk.reduce(
    (sum, row) => sum + row.borrower.exposureCr,
    0,
  );
  const totalExposure = rows.reduce(
    (sum, row) => sum + row.borrower.exposureCr,
    0,
  );

  return (
    <div className="kpis">
      <div className="kpi" style={{ "--kc": "var(--idbi-bright)" } as CSSProperties}>
        <div className="kpi-label">Accounts monitored</div>
        <div className="kpi-value">{rows.length}</div>
        <div className="kpi-sub">
          seeded MSME book · ₹{totalExposure.toFixed(1)} Cr exposure
        </div>
      </div>
      <div className="kpi" style={{ "--kc": "var(--red)" } as CSSProperties}>
        <div className="kpi-label">High-risk (PD &ge; 15%)</div>
        <div className="kpi-value">{highRisk.length}</div>
        <div className="kpi-sub">
          <span className="warn">₹{highRiskExposure.toFixed(1)} Cr</span> exposure
          at risk
        </div>
      </div>
      <div className="kpi" style={{ "--kc": "var(--amber)" } as CSSProperties}>
        <div className="kpi-label">Scored this batch</div>
        <div className="kpi-value">
          {scored.length}
          <small>/ {rows.length}</small>
        </div>
        <div className="kpi-sub">POST /score · SHAP reason codes attached</div>
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
