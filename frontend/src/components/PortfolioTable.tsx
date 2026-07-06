import type { ScoredBorrower } from "../types";
import { formatPd } from "../format";

interface PortfolioTableProps {
  rows: ScoredBorrower[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const PD_BAR_CEILING = 0.25;

export function PortfolioTable({
  rows,
  selectedId,
  onSelect,
}: PortfolioTableProps) {
  return (
    <div className="panel">
      <div className="p-head">
        <div className="p-title">Portfolio</div>
        <div className="p-sub">MSME accounts · sorted by 12-mo PD</div>
        <div className="p-right">{rows.length} accounts · live scored</div>
      </div>
      <table className="portfolio">
        <thead>
          <tr>
            <th>Borrower</th>
            <th>Sector</th>
            <th>Exposure</th>
            <th>Grade</th>
            <th>PD 12-mo</th>
            <th>Watch tier</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ borrower, score, error }) => {
            const barWidth = score
              ? Math.min(100, (score.pd / PD_BAR_CEILING) * 100)
              : 0;
            return (
              <tr
                key={borrower.id}
                className={borrower.id === selectedId ? "sel" : undefined}
                onClick={() => onSelect(borrower.id)}
              >
                <td>
                  <div className="b-name">{borrower.name}</div>
                  <div className="b-sub">
                    {borrower.account} · {borrower.region}
                  </div>
                </td>
                <td className="tier">{borrower.sector}</td>
                <td>{borrower.exposure}</td>
                <td>
                  {score ? (
                    <span className={`grade-tag grade-${score.grade}`}>
                      {score.grade}
                    </span>
                  ) : (
                    <span className="cell-muted">—</span>
                  )}
                </td>
                <td>
                  {score ? (
                    <div className="pd-cell">
                      <span className="pd-num">{formatPd(score.pd)}</span>
                      <span className="pd-bar">
                        <span
                          className="pd-fill"
                          style={{ width: `${barWidth}%` }}
                        />
                      </span>
                    </div>
                  ) : (
                    <span className="cell-status">
                      {error ?? "not scored"}
                    </span>
                  )}
                </td>
                <td className="tier">
                  {score ? score.watch_tier : <span className="cell-muted">—</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
