export function calculateSlope(
  elevations: number[],
  distances: number[],
  windowSize = 5
): number[] {
  const slopes: number[] = [];
  const halfWindow = Math.floor(windowSize / 2);

  for (let i = 0; i < elevations.length; i++) {
    const start = Math.max(0, i - halfWindow);
    const end = Math.min(elevations.length - 1, i + halfWindow);

    if (start === end) {
      slopes.push(0);
      continue;
    }

    const deltaEle = elevations[end] - elevations[start];
    const deltaDist = distances[end] - distances[start];
    slopes.push(deltaDist > 0 ? (deltaEle / deltaDist) * 100 : 0);
  }

  return slopes;
}

export function getSlopeColor(slope: number): string {
  if (slope > 8) return '#dc2626';
  if (slope > 4) return '#ef4444';
  if (slope > 1) return '#f87171';
  if (slope > -1) return '#9ca3af';
  if (slope > -4) return '#60a5fa';
  if (slope > -8) return '#3b82f6';
  return '#1d4ed8';
}

export function getSlopeLabel(slope: number): string {
  if (slope > 8) return 'Steep climb';
  if (slope > 4) return 'Moderate climb';
  if (slope > 1) return 'Slight climb';
  if (slope > -1) return 'Flat';
  if (slope > -4) return 'Slight descent';
  if (slope > -8) return 'Moderate descent';
  return 'Steep descent';
}

export function formatSlope(slope: number): { text: string; color: string; label: string } {
  const sign = slope >= 0 ? '+' : '';
  return {
    text: `${sign}${slope.toFixed(1)}%`,
    color: getSlopeColor(slope),
    label: getSlopeLabel(slope),
  };
}
