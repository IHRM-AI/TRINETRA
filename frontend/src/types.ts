import type { Borrower } from "./data/portfolio";
import type { ScoreResponse } from "./api/types";

export interface ScoredBorrower {
  borrower: Borrower;
  score: ScoreResponse | null;
  error: string | null;
}
