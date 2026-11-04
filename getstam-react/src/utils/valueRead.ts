import { MarketOverviewEntry } from './trendAnalysis';

export type ValueVerdict = 'value' | 'fair' | 'pass';

export interface ValueRead {
  price: number;      // American odds for the lean side
  breakEven: number;  // 0-1, win rate needed to break even at `price`
  adjusted: number;   // 0-1, lean probability pulled toward breakEven for small n
  verdict: ValueVerdict;
}

// A 70% rate on 10 games is a thin sample: blend in this many games at the
// break-even rate so small samples can't produce a VALUE verdict on their own.
const PRIOR_GAMES = 10;
// Edge (adjusted - breakEven) needed before calling it VALUE / PASS.
const VALUE_MARGIN = 0.02;

export const breakEvenRate = (price: number): number =>
  price < 0 ? -price / (-price + 100) : 100 / (price + 100);

export const shrinkRate = (rate: number, n: number, breakEven: number): number =>
  (rate * n + breakEven * PRIOR_GAMES) / (n + PRIOR_GAMES);

const leanPrice = (market: 'moneyline' | 'spread' | 'total', lean: string, game: any): number | null => {
  if (market === 'total') {
    const price = lean === 'Over' ? game?.totals?.over_price : game?.totals?.under_price;
    return price ?? null;
  }
  const side = game?.home?.team === lean ? game.home : game?.away?.team === lean ? game.away : null;
  if (!side) return null;
  return (market === 'moneyline' ? side.odds?.h2h : side.odds?.spread_price) ?? null;
};

export const getValueRead = (
  market: 'moneyline' | 'spread' | 'total',
  entry: MarketOverviewEntry,
  game: any,
): ValueRead | null => {
  const price = leanPrice(market, entry.lean, game);
  if (price == null || price === 0) return null;
  const breakEven = breakEvenRate(price);
  const adjusted = shrinkRate(entry.probability, entry.sample_size, breakEven);
  const edge = adjusted - breakEven;
  const verdict: ValueVerdict = edge >= VALUE_MARGIN ? 'value' : edge <= -VALUE_MARGIN ? 'pass' : 'fair';
  return { price, breakEven, adjusted, verdict };
};
