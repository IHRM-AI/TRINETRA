import { useCallback, useEffect, useState } from "react";
import { ApiError, getHealth, getPortfolio, score } from "./api/client";
import type { Account, HealthResponse, PortfolioSummary } from "./api/types";
import type { Borrower } from "./data/portfolio";
import type { ScoredBorrower } from "./types";

type LoadPhase = "loading" | "ready" | "error";

interface PortfolioScores {
  rows: ScoredBorrower[];
  summary: PortfolioSummary | null;
  health: HealthResponse | null;
  healthError: boolean;
  phase: LoadPhase;
  backendDown: boolean;
  reload: () => void;
  addBorrower: (borrower: Borrower) => Promise<ScoredBorrower>;
}

function describe(cause: unknown): string {
  if (cause instanceof ApiError) {
    return cause.status === 0 ? "backend unreachable" : cause.message;
  }
  return cause instanceof Error ? cause.message : "scoring failed";
}

function toRow(account: Account): ScoredBorrower {
  return {
    borrower: {
      id: account.id,
      name: account.name,
      account: account.account,
      sector: account.sector,
      region: account.region,
      exposure: `₹${account.exposure_cr} Cr`,
      exposureCr: account.exposure_cr,
      features: account.features,
    },
    score: {
      pd: account.pd,
      grade: account.grade,
      watch_tier: account.watch_tier,
      reason_codes: [],
    },
    error: null,
  };
}

export function usePortfolioScores(): PortfolioScores {
  const [rows, setRows] = useState<ScoredBorrower[]>([]);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [phase, setPhase] = useState<LoadPhase>("loading");
  const [nonce, setNonce] = useState(0);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  const addBorrower = useCallback(async (borrower: Borrower) => {
    let scored: ScoredBorrower;
    try {
      scored = { borrower, score: await score(borrower.features), error: null };
    } catch (cause) {
      scored = { borrower, score: null, error: describe(cause) };
    }
    setRows((prev) => [...prev, scored].sort((a, b) => (b.score?.pd ?? -1) - (a.score?.pd ?? -1)));
    return scored;
  }, []);

  useEffect(() => {
    let cancelled = false;
    setPhase("loading");

    async function run() {
      const healthResult = await getHealth().then(
        (value) => ({ ok: true as const, value }),
        () => ({ ok: false as const }),
      );
      if (!cancelled) {
        setHealth(healthResult.ok ? healthResult.value : null);
        setHealthError(!healthResult.ok);
      }

      try {
        const portfolio = await getPortfolio(240);
        if (cancelled) return;
        setRows(portfolio.accounts.map(toRow));
        setSummary(portfolio.summary);
        setPhase("ready");
      } catch {
        if (!cancelled) setPhase("error");
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [nonce]);

  const backendDown = healthError && rows.length === 0;

  return { rows, summary, health, healthError, phase, backendDown, reload, addBorrower };
}
