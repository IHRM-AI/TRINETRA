export function formatPd(pd: number): string {
  return `${(pd * 100).toFixed(1)}%`;
}

export function formatPp(pp: number): string {
  const sign = pp > 0 ? "+" : pp < 0 ? "−" : "";
  return `${sign}${Math.abs(pp).toFixed(1)}pp`;
}
