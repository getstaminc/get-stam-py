import { computePropStreak } from './propStreaks';

describe('computePropStreak', () => {
  it('counts the current consecutive run in the most-recent direction', () => {
    const historical = [
      { actual_x: 2, odds_x: 1 }, // over
      { actual_x: 3, odds_x: 1 }, // over
      { actual_x: 0, odds_x: 1 }, // under (streak break)
      { actual_x: 2, odds_x: 1 }, // over
    ];
    const result = computePropStreak(historical, 'actual_x', 'odds_x');
    expect(result).toEqual({
      direction: 'over',
      count: 2,
      continuation_rate: 0.75,
      sample_size: 4,
      recentHits: [true, true, false, true],
    });
  });

  it('returns null when there is no usable historical data', () => {
    expect(computePropStreak([], 'actual_x', 'odds_x')).toBeNull();
    expect(computePropStreak([{ actual_x: null, odds_x: 1 }], 'actual_x', 'odds_x')).toBeNull();
  });

  it('returns null when the most recent game is an exact push', () => {
    expect(computePropStreak([{ actual_x: 1, odds_x: 1 }], 'actual_x', 'odds_x')).toBeNull();
  });
});
