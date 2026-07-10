import type { ReasonCode } from "../api/types";
import { formatLogOdds } from "../format";

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
    ...codes.map((code) => Math.abs(code.contribution_logodds)),
    1,
  );

  return (
    <>
      <div className="shap">
        {codes.map((code, index) => {
          const positive = code.contribution_logodds > 0;
          const width = (Math.abs(code.contribution_logodds) / maxMagnitude) * 50;
          return (
            <div className="shap-row" key={`${code.code}-${index}`}>
              <div className="shap-lab">
                <span>
                  {code.label}
                  <span className="code">{code.code}</span>
                </span>
                <span className={`v ${positive ? "pos" : "neg"}`}>
                  {formatLogOdds(code.contribution_logodds)}
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
        Contributions are SHAP log-odds margins from the segment model, mapped
        to the RBI EWS trigger taxonomy. Sign gives direction; magnitude ranks
        drivers. Values are on the log-odds scale, not percentage points of PD.
      </div>
    </>
  );
}
