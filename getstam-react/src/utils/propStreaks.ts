export interface PropStreak {
  direction: 'over' | 'under';
  count: number;
  continuation_rate: number;
  sample_size: number;
  // Up to 5 entries, most-recent-first; true = that game matched `direction`.
  recentHits: boolean[];
}

type Direction = 'over' | 'under' | null;

const directionOf = (actual: any, odds: any): Direction => {
  if (actual == null || odds == null || isNaN(Number(actual)) || isNaN(Number(odds))) return null;
  if (Number(actual) > Number(odds)) return 'over';
  if (Number(actual) < Number(odds)) return 'under';
  return null; // push
};

// Derives a "streak" purely from historical rows already present on each
// player-prop response (no new data) — the current direction's run length,
// how often that direction has held across the full sample, and a last-5
// hit/miss strip for it.
export function computePropStreak(historical: any[], actualKey: string, oddsKey: string): PropStreak | null {
  const rows = historical.filter((h) => directionOf(h[actualKey], h[oddsKey]) != null);
  if (rows.length === 0) return null;

  const direction = directionOf(rows[0][actualKey], rows[0][oddsKey]);
  if (!direction) return null;

  let count = 0;
  for (const row of rows) {
    if (directionOf(row[actualKey], row[oddsKey]) === direction) count++;
    else break;
  }

  const matches = rows.filter((row) => directionOf(row[actualKey], row[oddsKey]) === direction).length;
  const recentHits = rows.slice(0, 5).map((row) => directionOf(row[actualKey], row[oddsKey]) === direction);

  return {
    direction,
    count,
    continuation_rate: matches / rows.length,
    sample_size: rows.length,
    recentHits,
  };
}
