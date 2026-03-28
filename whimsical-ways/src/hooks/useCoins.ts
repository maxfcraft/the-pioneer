import { useMemo } from 'react';
import { stepsToCoin } from '../utils/coins';

export function useCoins(steps: number) {
  const coins = useMemo(() => stepsToCoin(steps), [steps]);
  return coins;
}
