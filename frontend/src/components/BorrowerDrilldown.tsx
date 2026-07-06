import type { ScoredBorrower } from "../types";
import { formatPd } from "../format";
import { ReasonCodes } from "./ReasonCodes";

interface BorrowerDrilldownProps {
  selected: ScoredBorrower | null;
}

export function BorrowerDrilldown({ selected }: BorrowerDrilldownProps) {
  if (selected === null) {
    return (
      <div className="panel">
        <div className="p-head">
          <div className="p-title">Borrower drill-down</div>
        </div>
        <div className="state">Select a borrower to inspect its risk profile.</div>
      </div>
    );
  }

  const { borrower, score, error } = selected;

  return (
    <div className="panel">
      <div className="dd-head">
        <div className="dd-name">{borrower.name}</div>
        {score && (
          <>
            <span className={`chip chip-${gradeChip(score.grade)}`}>
              Grade {score.grade}
            </span>
            <span className="chip chip-red">
              12-mo PD {formatPd(score.pd)}
            </span>
            <span className="chip chip-slate">{score.watch_tier}</span>
          </>
        )}
        <span className="chip chip-slate">Exposure {borrower.exposure}</span>
        <span className="dd-meta" style={{ marginLeft: "auto" }}>
          {borrower.account} · {borrower.sector} · {borrower.region}
        </span>
      </div>
      <div className="dd-body">
        <div className="dd-col-title">Why flagged — SHAP → RBI EWS reason codes</div>
        <div className="dd-col-sub">contribution to 12-mo PD, percentage points</div>
        {score ? (
          <ReasonCodes codes={score.reason_codes} />
        ) : (
          <div className="state error">
            {error ?? "This borrower could not be scored."}
          </div>
        )}
      </div>
    </div>
  );
}

function gradeChip(grade: string): "teal" | "amber" | "red" {
  if (grade === "A" || grade === "B") return "teal";
  if (grade === "C") return "amber";
  return "red";
}
