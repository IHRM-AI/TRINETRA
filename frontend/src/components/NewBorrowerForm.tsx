import { useState } from "react";

import type { Features } from "../api/types";
import type { Borrower } from "../data/portfolio";
import type { ScoredBorrower } from "../types";

interface Props {
  addBorrower: (borrower: Borrower) => Promise<ScoredBorrower>;
  onAdded: (id: string) => void;
}

interface Field {
  key: string;
  label: string;
  value: number;
  step?: number;
}

const DEFAULTS: Field[] = [
  { key: "PERFORM_CNS.SCORE", label: "Bureau score (300–900)", value: 620 },
  { key: "ltv", label: "Loan-to-value (0–1)", value: 0.85, step: 0.01 },
  { key: "primary_utilization", label: "Limit utilisation (0–1.2)", value: 0.7, step: 0.01 },
  { key: "PRI.OVERDUE.ACCTS", label: "Overdue accounts", value: 1 },
  { key: "DELINQUENT.ACCTS.IN.LAST.SIX.MONTHS", label: "Delinquencies (6m)", value: 0 },
  { key: "NO.OF_INQUIRIES", label: "Bureau enquiries (90d)", value: 2 },
  { key: "age_years", label: "Promoter age", value: 44 },
  { key: "credit_history_months", label: "Credit history (months)", value: 90 },
];

export function NewBorrowerForm({ addBorrower, onAdded }: Props) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [sector, setSector] = useState("");
  const [exposureCr, setExposureCr] = useState(5);
  const [fields, setFields] = useState<Field[]>(DEFAULTS);
  const [busy, setBusy] = useState(false);

  const update = (key: string, raw: string) =>
    setFields((prev) => prev.map((f) => (f.key === key ? { ...f, value: Number(raw) } : f)));

  const submit = async () => {
    setBusy(true);
    const entered = Object.fromEntries(fields.map((f) => [f.key, f.value]));
    const overdue = Number(entered["PRI.OVERDUE.ACCTS"]);
    const features: Features = {
      ...entered,
      overdue_ratio: overdue / (overdue + 8),
      disbursed_amount: exposureCr * 1e7,
      asset_cost: (exposureCr * 1e7) / (Number(entered.ltv) || 0.85),
      "Employment.Type": "Self employed",
      State_ID: 4,
      manufacturer_id: 45,
    };
    const borrower: Borrower = {
      id: `new-${Date.now()}`,
      name: name || "New account",
      account: "A/c —",
      sector: sector || "Unspecified",
      region: "Manual entry",
      exposure: `₹${exposureCr} Cr`,
      exposureCr,
      features,
    };
    const scored = await addBorrower(borrower);
    setBusy(false);
    setOpen(false);
    if (scored.score) onAdded(borrower.id);
  };

  if (!open) {
    return (
      <button className="add-toggle" onClick={() => setOpen(true)}>
        + Score a new account
      </button>
    );
  }

  return (
    <div className="panel add-form">
      <div className="p-head">
        <div className="p-title">Score a new account</div>
        <button className="retry" onClick={() => setOpen(false)}>
          Cancel
        </button>
      </div>
      <div className="add-grid">
        <label>
          Borrower name
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme Textiles Pvt Ltd" />
        </label>
        <label>
          Sector
          <input value={sector} onChange={(e) => setSector(e.target.value)} placeholder="Textiles" />
        </label>
        <label>
          Exposure (₹ Cr)
          <input type="number" value={exposureCr} step={0.1} onChange={(e) => setExposureCr(Number(e.target.value))} />
        </label>
        {fields.map((f) => (
          <label key={f.key}>
            {f.label}
            <input type="number" value={f.value} step={f.step ?? 1} onChange={(e) => update(f.key, e.target.value)} />
          </label>
        ))}
      </div>
      <button className="add-submit" onClick={submit} disabled={busy}>
        {busy ? "Scoring…" : "Score account"}
      </button>
    </div>
  );
}
