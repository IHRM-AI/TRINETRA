import type { HealthResponse } from "../api/types";
import { Logo } from "./Logo";

interface HeaderProps {
  health: HealthResponse | null;
  healthError: boolean;
}

function healthState(health: HealthResponse | null, healthError: boolean) {
  if (healthError || health === null) {
    return { className: "offline", label: "Backend unreachable" };
  }
  if (health.model_loaded) {
    const genai = health.genai_available ? "GenAI online" : "GenAI offline";
    return { className: "online", label: `Model loaded · ${genai}` };
  }
  return { className: "degraded", label: "Model not loaded" };
}

export function Header({ health, healthError }: HeaderProps) {
  const status = healthState(health, healthError);

  return (
    <header className="header">
      <div className="brand">
        <Logo className="brand-mark" />
        <div>
          <div className="brand-name">TRINETRA</div>
          <div className="brand-sub">MSME Early-Warning</div>
        </div>
      </div>
      <div className="header-spacer" />
      <div className="health">
        <span className={`health-dot ${status.className}`} />
        {status.label}
      </div>
      <div className="cobrand">
        <span className="sq" />
        IDBI BANK · EWS AUGMENTATION LAYER
      </div>
    </header>
  );
}
