import { useMemo } from "react";

import type { ScoredBorrower } from "../types";

const GRADES = ["A", "B", "C", "D", "E"] as const;
const GRADE_COLOR: Record<string, string> = {
  A: "0, 131, 108",
  B: "63, 153, 90",
  C: "217, 133, 43",
  D: "200, 96, 50",
  E: "193, 82, 78",
};

export function PortfolioHeatmap({ rows }: { rows: ScoredBorrower[] }) {
  const { sectors, counts, max } = useMemo(() => {
    const table = new Map<string, Record<string, number>>();
    for (const row of rows) {
      if (!row.score) continue;
      const cells = table.get(row.borrower.sector) ?? {};
      cells[row.score.grade] = (cells[row.score.grade] ?? 0) + 1;
      table.set(row.borrower.sector, cells);
    }
    const ordered = [...table.entries()]
      .map(([sector, cells]) => ({
        sector,
        cells,
        total: Object.values(cells).reduce((a, b) => a + b, 0),
      }))
      .sort((a, b) => b.total - a.total)
      .slice(0, 8);
    const peak = Math.max(1, ...ordered.flatMap((s) => Object.values(s.cells)));
    return { sectors: ordered, counts: table, max: peak };
  }, [rows]);

  void counts;
  if (sectors.length === 0) return null;

  return (
    <div className="panel heatmap">
      <div className="p-head">
        <div className="p-title">Portfolio risk heatmap</div>
        <div className="p-sub">sector × grade · account count</div>
      </div>
      <div className="hm-grid">
        <div className="hm-corner" />
        {GRADES.map((grade) => (
          <div key={grade} className="hm-col">
            {grade}
          </div>
        ))}
        {sectors.map(({ sector, cells }) => (
          <Row key={sector} sector={sector} cells={cells} max={max} />
        ))}
      </div>
    </div>
  );
}

function Row({
  sector,
  cells,
  max,
}: {
  sector: string;
  cells: Record<string, number>;
  max: number;
}) {
  return (
    <>
      <div className="hm-row-label">{sector}</div>
      {GRADES.map((grade) => {
        const count = cells[grade] ?? 0;
        const alpha = count === 0 ? 0.04 : 0.18 + 0.7 * (count / max);
        return (
          <div
            key={grade}
            className="hm-cell"
            style={{ background: `rgba(${GRADE_COLOR[grade]}, ${alpha})` }}
          >
            {count > 0 ? count : ""}
          </div>
        );
      })}
    </>
  );
}
