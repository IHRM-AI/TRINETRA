import type { ScoredBorrower } from "../types";
import { formatPd } from "../format";

interface NextActionWorklistProps {
  rows: ScoredBorrower[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const GRADE_RANK: Record<string, number> = { E: 0, D: 1, C: 2, B: 3, A: 4 };
const WORKLIST_LIMIT = 12;

function actionClass(action: string | undefined): string {
  if (action === "Exit / RFA review") return "act-exit";
  if (action === "Restructure or collateral top-up") return "act-restructure";
  if (action === "Enhanced monitoring + covenant check") return "act-monitor";
  return "act-standard";
}

export function NextActionWorklist({
  rows,
  selectedId,
  onSelect,
}: NextActionWorklistProps) {
  const ranked = rows
    .filter((row) => row.score)
    .slice()
    .sort((a, b) => {
      const gradeDelta =
        (GRADE_RANK[a.score!.grade] ?? 9) - (GRADE_RANK[b.score!.grade] ?? 9);
      return gradeDelta !== 0 ? gradeDelta : b.score!.pd - a.score!.pd;
    })
    .slice(0, WORKLIST_LIMIT);

  return (
    <div className="panel">
      <div className="p-head">
        <div className="p-title">Next best action</div>
        <div className="p-sub">Officer worklist · highest-risk first</div>
        <div className="p-right">
          {ranked.length} of {rows.length} accounts
        </div>
      </div>
      {ranked.length === 0 ? (
        <div className="state">No scored accounts to queue.</div>
      ) : (
        <table className="portfolio worklist">
          <thead>
            <tr>
              <th>Borrower</th>
              <th>Exposure</th>
              <th>PD 12-mo</th>
              <th>Recommended action</th>
            </tr>
          </thead>
          <tbody>
            {ranked.map(({ borrower, score }) => (
              <tr
                key={borrower.id}
                className={borrower.id === selectedId ? "sel" : undefined}
                onClick={() => onSelect(borrower.id)}
              >
                <td>
                  <div className="b-name">{borrower.name}</div>
                  <div className="b-sub">
                    <span className={`grade-tag grade-${score!.grade}`}>
                      {score!.grade}
                    </span>{" "}
                    {borrower.sector}
                  </div>
                </td>
                <td>{borrower.exposure}</td>
                <td className="pd-num">{formatPd(score!.pd)}</td>
                <td>
                  <span className={`action-tag ${actionClass(borrower.nextAction)}`}>
                    {borrower.nextAction ?? "—"}
                  </span>
                  {borrower.actionReason && (
                    <div className="action-reason">{borrower.actionReason}</div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="worklist-foot">
        Rule-based routing from grade, watch tier and PD. Click a row to open the
        drill-down.
      </div>
    </div>
  );
}
