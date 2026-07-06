import type { ReasonCode } from "../api/types";
import { formatPp } from "../format";

interface ReasonCodesProps {
  codes: ReasonCode[];
}

export function ReasonCodes({ codes }: ReasonCodesProps) {
  if (codes.length === 0) {
    return (
      <div className="dd-col-sub" style={{ marginTop: 8 }}>
        No trigger reached the reporting threshold for this account.
      </div>
    );
  }

  const maxMagnitude = Math.max(
    ...codes.map((code) => Math.abs(code.contribution_pp)),
    1,
  );

  return (
    <>
      <div className="shap">
        {codes.map((code, index) => {
          const positive = code.contribution_pp > 0;
          const width = (Math.abs(code.contribution_pp) / maxMagnitude) * 50;
          return (
            <div className="shap-row" key={`${code.code}-${index}`}>
              <div className="shap-lab">
                <span>
                  {code.label}
                  <span className="code">{code.code}</span>
                </span>
                <span className={`v ${positive ? "pos" : "neg"}`}>
                  {formatPp(code.contribution_pp)}
                </span>
              </div>
              <div className="shap-track">
                <span
                  className={`shap-bar ${positive ? "sb-pos" : "sb-neg"}`}
                  style={{ width: `${width}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <div className="shap-axis">
        <span>reduces risk</span>
        <span>increases risk</span>
      </div>
      <div className="shap-note">
        Contributions in percentage points from the segment SHAP explainer,
        mapped to the RBI EWS trigger taxonomy.
      </div>
    </>
  );
}
