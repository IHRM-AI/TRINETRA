import { useEffect, useState } from "react";

import { getBenchmark } from "../api/client";
import type { BenchmarkResponse, CapturePoint } from "../api/types";

const W = 460;
const H = 240;
const PAD = 34;

function path(points: CapturePoint[]): string {
  return points
    .map((point, index) => {
      const x = PAD + point.flag_rate * (W - 2 * PAD);
      const y = H - PAD - point.capture * (H - 2 * PAD);
      return `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");
}

export function CaptureCurve() {
  const [data, setData] = useState<BenchmarkResponse | null>(null);

  useEffect(() => {
    let active = true;
    getBenchmark()
      .then((response) => active && setData(response))
      .catch(() => active && setData(null));
    return () => {
      active = false;
    };
  }, []);

  if (!data) return null;

  const modelAt20 = Math.round(data.capture_at_20pct.model * 100);
  const ruleAt20 = Math.round(data.capture_at_20pct.rule_baseline * 100);
  const gain = modelAt20 - ruleAt20;
  const markerX = PAD + 0.2 * (W - 2 * PAD);

  return (
    <div className="panel capture">
      <div className="p-head">
        <div className="p-title">Default capture curve</div>
        <div className="p-sub">out-of-time · L&amp;T segment · AUC {data.metrics.auc.toFixed(2)}</div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H}>
        <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={PAD} stroke="#22324a" strokeDasharray="3 3" />
        <line x1={markerX} y1={PAD} x2={markerX} y2={H - PAD} stroke="#39506e" strokeDasharray="2 3" />
        <path d={path(data.capture_curve_rule)} fill="none" stroke="#ffb454" strokeWidth={2.5} />
        <path d={path(data.capture_curve_model)} fill="none" stroke="#2dd4bf" strokeWidth={2.5} />
        <circle cx={markerX} cy={H - PAD - data.capture_at_20pct.model * (H - 2 * PAD)} r={4} fill="#2dd4bf" />
        <circle cx={markerX} cy={H - PAD - data.capture_at_20pct.rule_baseline * (H - 2 * PAD)} r={4} fill="#ffb454" />
        <text x={PAD} y={H - 10} fontSize={10} fill="#5b6c8c">
          % of book flagged
        </text>
      </svg>
      <div className="capture-legend">
        <span>
          <i style={{ background: "#2dd4bf" }} /> TRINETRA {modelAt20}%
        </span>
        <span>
          <i style={{ background: "#ffb454" }} /> Rule EWS {ruleAt20}%
        </span>
        <span className="capture-gain">+{gain}pp caught at a 20% flag budget</span>
      </div>
    </div>
  );
}
