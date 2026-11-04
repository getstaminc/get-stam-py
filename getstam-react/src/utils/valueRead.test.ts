import { breakEvenRate, shrinkRate, getValueRead } from './valueRead';

const game = {
  home: { team: 'New York Knicks', odds: { h2h: -120, spread_point: -4.5, spread_price: -110 } },
  away: { team: 'Charlotte Hornets', odds: { h2h: 100, spread_point: 4.5, spread_price: -110 } },
  totals: { over_point: 221.5, over_price: -110, under_point: 221.5, under_price: -110 },
};

const entry = (lean: string, probability: number, sample_size = 25) => ({
  lean, probability, sample_size, trend_count: 1, contributing_trends: [],
});

describe('breakEvenRate', () => {
  it('converts favorite prices', () => {
    expect(breakEvenRate(-120)).toBeCloseTo(0.5455, 4);
    expect(breakEvenRate(-500)).toBeCloseTo(0.8333, 4);
  });
  it('converts underdog prices', () => {
    expect(breakEvenRate(150)).toBeCloseTo(0.4, 4);
    expect(breakEvenRate(100)).toBeCloseTo(0.5, 4);
  });
});

describe('shrinkRate', () => {
  it('pulls small samples toward break-even with 10 games of weight', () => {
    // (0.7*10 + 0.5*10) / 20
    expect(shrinkRate(0.7, 10, 0.5)).toBeCloseTo(0.6, 4);
  });
  it('barely moves large samples', () => {
    expect(shrinkRate(0.7, 1000, 0.5)).toBeCloseTo(0.698, 3);
  });
});

describe('getValueRead', () => {
  it('flags VALUE when the adjusted rate clears break-even by 2+ points', () => {
    const read = getValueRead('moneyline', entry('New York Knicks', 0.7, 50), game)!;
    expect(read.price).toBe(-120);
    expect(read.breakEven).toBeCloseTo(0.5455, 4);
    expect(read.verdict).toBe('value');
  });

  it('flags PASS for a strong lean at a steep price', () => {
    const steep = { ...game, home: { ...game.home, odds: { ...game.home.odds, h2h: -500 } } };
    expect(getValueRead('moneyline', entry('New York Knicks', 0.7, 50), steep)!.verdict).toBe('pass');
  });

  it('flags FAIR when the edge is under 2 points either way', () => {
    // adjusted = (0.56*25 + 0.5455*10)/35 ≈ 0.5559 → edge ≈ +1.0
    expect(getValueRead('moneyline', entry('New York Knicks', 0.56), game)!.verdict).toBe('fair');
  });

  it('uses the lean team spread price and the over/under price', () => {
    expect(getValueRead('spread', entry('Charlotte Hornets', 0.6), game)!.price).toBe(-110);
    expect(getValueRead('total', entry('Over', 0.6), game)!.price).toBe(-110);
    const underGame = { ...game, totals: { ...game.totals, under_price: 105 } };
    expect(getValueRead('total', entry('Under', 0.6), underGame)!.price).toBe(105);
  });

  it('returns null when there is no price for the lean', () => {
    const noOdds = { ...game, home: { team: 'New York Knicks', odds: {} } };
    expect(getValueRead('moneyline', entry('New York Knicks', 0.7), noOdds)).toBeNull();
    expect(getValueRead('moneyline', entry('Someone Else', 0.7), game)).toBeNull();
  });
});
