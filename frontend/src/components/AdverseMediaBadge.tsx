import { useEffect, useState } from "react";

import { checkAdverseMedia } from "../api/client";
import type { AdverseMediaResponse } from "../api/types";

interface AdverseMediaBadgeProps {
  borrowerName: string;
  borrowerId: string;
  grade: string;
}

export function AdverseMediaBadge({
  borrowerName,
  borrowerId,
  grade,
}: AdverseMediaBadgeProps) {
  const [result, setResult] = useState<AdverseMediaResponse | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setResult(null);
    setFailed(false);
    let active = true;
    checkAdverseMedia(borrowerName, grade)
      .then((value) => active && setResult(value))
      .catch(() => active && setFailed(true));
    return () => {
      active = false;
    };
  }, [borrowerId, borrowerName, grade]);

  if (failed || result === null || !result.escalate) {
    return null;
  }

  return (
    <div className="adverse">
      <div className="adverse-head">
        <span className="adverse-flag">Adverse media</span>
        {result.is_demo_fixture && (
          <span className="adverse-demo">labelled demo fixture</span>
        )}
        {result.tier_escalation && (
          <span className="chip chip-red">Escalate → {result.tier_escalation}</span>
        )}
      </div>
      <div className="adverse-summary">{result.summary}</div>
      {result.sources.length > 0 && (
        <ul className="adverse-sources">
          {result.sources.map((source) => (
            <li key={source.url}>
              <a href={source.url} target="_blank" rel="noreferrer">
                {source.title || source.url}
              </a>
            </li>
          ))}
        </ul>
      )}
      <div className="adverse-note">{result.overlay_note}</div>
    </div>
  );
}
