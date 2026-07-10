export function formatPd(pd: number): string {
  return `${(pd * 100).toFixed(1)}%`;
}

export function formatLogOdds(value: number): string {
  const sign = value > 0 ? "+" : value < 0 ? "−" : "";
  return `${sign}${Math.abs(value).toFixed(2)}`;
}
