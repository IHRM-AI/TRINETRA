import { useEffect, useState } from "react";

import { termStructure } from "../api/client";
import type { Features, TermStructureResponse } from "../api/types";

const W = 520;
const H = 150;
const PAD = 28;
const MONTHS = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"];

export function PdTermStructure({ features }: { features: Features }) {
  const [data, setData] = useState<TermStructureResponse | null>(null);

  useEffect(() => {
    let active = true;
    termStructure(features)
      .then((response) => active && setData(response))
      .catch(() => active && setData(null));
    return () => {
      active = false;
    };
  }, [features]);

  if (!data) return null;

  const values = data.marginal_pd;
  const max = Math.max(...values, 1e-4);
  const points = values.map((value, index) => {
    const x = PAD + (index / (values.length - 1)) * (W - 2 * PAD);
    const y = H - PAD - (value / max) * (H - 2 * PAD);
    return { x, y };
  });
  const line = points.map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(" ");
  const peak = points[data.peak_month - 1];

  return (
    <div className="term">
      <div className="dd-col-title">PD term structure — next 12 months</div>
      <div className="dd-col-sub">conditional monthly default probability · peaks month {data.peak_month}</div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H}>
        <path
          d={`${line} L ${points[points.length - 1].x} ${H - PAD} L ${points[0].x} ${H - PAD} Z`}
          fill="rgba(45,212,191,0.12)"
        />
        <path d={line} fill="none" stroke="#2dd4bf" strokeWidth={2.5} />
        {peak && (
          <>
            <line x1={peak.x} y1={peak.y} x2={peak.x} y2={H - PAD} stroke="#ffb454" strokeWidth={1} strokeDasharray="3 3" />
            <circle cx={peak.x} cy={peak.y} r={4} fill="#ffb454" />
          </>
        )}
        {MONTHS.map((label, index) => (
          <text
            key={label}
            x={PAD + (index / (values.length - 1)) * (W - 2 * PAD)}
            y={H - 8}
            fontSize={9}
            fill="#5b6c8c"
            textAnchor="middle"
          >
            {label}
          </text>
        ))}
      </svg>
    </div>
  );
}
