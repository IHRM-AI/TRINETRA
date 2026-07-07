import { useCallback, useEffect, useState } from "react";
import { ApiError, getHealth, score } from "./api/client";
import type { HealthResponse } from "./api/types";
import type { Borrower } from "./data/portfolio";
import { PORTFOLIO } from "./data/portfolio";
import type { ScoredBorrower } from "./types";

type LoadPhase = "loading" | "ready" | "error";

interface PortfolioScores {
  rows: ScoredBorrower[];
  health: HealthResponse | null;
  healthError: boolean;
  phase: LoadPhase;
  backendDown: boolean;
  reload: () => void;
  addBorrower: (borrower: Borrower) => Promise<ScoredBorrower>;
}

function byPd(a: ScoredBorrower, b: ScoredBorrower): number {
  return (b.score?.pd ?? -1) - (a.score?.pd ?? -1);
}

function describe(cause: unknown): string {
  if (cause instanceof ApiError) {
    return cause.status === 0 ? "backend unreachable" : cause.message;
  }
  return cause instanceof Error ? cause.message : "scoring failed";
}

async function scoreBorrower(borrower: Borrower): Promise<ScoredBorrower> {
  try {
    return { borrower, score: await score(borrower.features), error: null };
  } catch (cause) {
    return { borrower, score: null, error: describe(cause) };
  }
}

export function usePortfolioScores(): PortfolioScores {
  const [rows, setRows] = useState<ScoredBorrower[]>(
    PORTFOLIO.map((borrower) => ({ borrower, score: null, error: null })),
  );
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState(false);
  const [phase, setPhase] = useState<LoadPhase>("loading");
  const [nonce, setNonce] = useState(0);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  const addBorrower = useCallback(async (borrower: Borrower) => {
    const scored = await scoreBorrower(borrower);
    setRows((prev) => [...prev, scored].sort(byPd));
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

      const scored = await Promise.all(PORTFOLIO.map(scoreBorrower));
      if (cancelled) return;

      scored.sort(byPd);
      setRows(scored);

      const anyScored = scored.some((row) => row.score !== null);
      setPhase(anyScored || healthResult.ok ? "ready" : "error");
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [nonce]);

  const backendDown = healthError && rows.every((row) => row.score === null);

  return { rows, health, healthError, phase, backendDown, reload, addBorrower };
}
