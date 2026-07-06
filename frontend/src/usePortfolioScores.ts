import { useCallback, useEffect, useState } from "react";
import { ApiError, getHealth, score } from "./api/client";
import type { HealthResponse } from "./api/types";
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
}

function describe(cause: unknown): string {
  if (cause instanceof ApiError) {
    return cause.status === 0 ? "backend unreachable" : cause.message;
  }
  return cause instanceof Error ? cause.message : "scoring failed";
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

      const scored = await Promise.all(
        PORTFOLIO.map(async (borrower): Promise<ScoredBorrower> => {
          try {
            return { borrower, score: await score(borrower.features), error: null };
          } catch (cause) {
            return { borrower, score: null, error: describe(cause) };
          }
        }),
      );

      if (cancelled) return;

      scored.sort((a, b) => (b.score?.pd ?? -1) - (a.score?.pd ?? -1));
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

  return { rows, health, healthError, phase, backendDown, reload };
}
