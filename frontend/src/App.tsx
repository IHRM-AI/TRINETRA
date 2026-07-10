import { useEffect, useState } from "react";
import { Header } from "./components/Header";
import { KpiStrip } from "./components/KpiStrip";
import { PortfolioTable } from "./components/PortfolioTable";
import { NextActionWorklist } from "./components/NextActionWorklist";
import { PortfolioHeatmap } from "./components/PortfolioHeatmap";
import { CaptureCurve } from "./components/CaptureCurve";
import { BorrowerDrilldown } from "./components/BorrowerDrilldown";
import { CreditMemo } from "./components/CreditMemo";
import { NewBorrowerForm } from "./components/NewBorrowerForm";
import { usePortfolioScores } from "./usePortfolioScores";

export function App() {
  const { rows, summary, health, healthError, phase, backendDown, reload, addBorrower } =
    usePortfolioScores();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    if (selectedId === null && rows.length > 0) {
      setSelectedId(rows[0].borrower.id);
    }
  }, [rows, selectedId]);

  const selected =
    rows.find((row) => row.borrower.id === selectedId) ?? null;

  return (
    <div className="app">
      <Header health={health} healthError={healthError} />
      <div className="content">
        {backendDown && (
          <div className="banner">
            <span>
              Backend unreachable at the configured API base. Showing the seeded
              portfolio without live scores.
            </span>
            <button className="retry" onClick={reload}>
              Retry
            </button>
          </div>
        )}

        <div className="demo-note" role="note">
          Demo book — names and exposures are illustrative; probabilities of
          default are model-derived on public L&amp;T data.
        </div>

        <KpiStrip rows={rows} summary={summary} health={health} healthError={healthError} />

        {phase === "loading" ? (
          <div className="panel">
            <div className="state">
              <span className="spinner" />
              Scoring portfolio…
            </div>
          </div>
        ) : (
          <>
            <div className="grid-2">
              <PortfolioHeatmap rows={rows} />
              <CaptureCurve />
            </div>
            <NewBorrowerForm addBorrower={addBorrower} onAdded={setSelectedId} />
            <NextActionWorklist
              rows={rows}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
            <PortfolioTable
              rows={rows}
              selectedId={selectedId}
              onSelect={setSelectedId}
            />
            <div className="grid-2">
              <BorrowerDrilldown selected={selected} />
              {selected ? (
                <CreditMemo borrower={selected.borrower} />
              ) : (
                <div className="panel">
                  <div className="p-head">
                    <div className="p-title">GenAI credit memo — draft</div>
                  </div>
                  <div className="state">Select a borrower to draft a memo.</div>
                </div>
              )}
            </div>
          </>
        )}

        <div className="footer">
          <span>
            <b>Augments existing EWS</b> (RBI Master Directions Jul 2024) ·
            <b> DPDP-compliant</b> · Demo on public-data models — retrains on
            bank book in sandbox
          </span>
        </div>
      </div>
    </div>
  );
}
