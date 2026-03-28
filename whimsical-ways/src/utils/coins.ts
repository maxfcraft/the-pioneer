// 1 step = 1 coin, simple and clean
export function stepsToCoin(steps: number): number {
  return steps;
}

export function formatCoins(coins: number): string {
  if (coins >= 1_000_000) {
    return `${(coins / 1_000_000).toFixed(1)}M`;
  }
  if (coins >= 1_000) {
    return `${(coins / 1_000).toFixed(1)}K`;
  }
  return coins.toLocaleString();
}

export function formatSteps(steps: number): string {
  return steps.toLocaleString();
}
