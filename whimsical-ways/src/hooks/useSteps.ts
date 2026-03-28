import { useState, useEffect } from 'react';
import { Pedometer } from 'expo-sensors';
import { getTodayStart } from '../utils/dateHelpers';

export function useSteps() {
  const [steps, setSteps] = useState(0);
  const [available, setAvailable] = useState(false);

  useEffect(() => {
    let subscription: { remove: () => void } | null = null;

    async function setup() {
      const isAvailable = await Pedometer.isAvailableAsync();
      setAvailable(isAvailable);

      if (!isAvailable) return;

      // Get today's step count so far
      const start = getTodayStart();
      const end = new Date();
      try {
        const result = await Pedometer.getStepCountAsync(start, end);
        setSteps(result.steps);
      } catch {
        // Pedometer may not have data yet
      }

      // Subscribe to live updates
      subscription = Pedometer.watchStepCount((result) => {
        setSteps((prev) => prev + result.steps);
      });
    }

    setup();

    return () => {
      subscription?.remove();
    };
  }, []);

  return { steps, available };
}
