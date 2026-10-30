import { hasNoOdds, hasFinalScore, hasLiveScore, shouldDisplayGame } from './gameDisplay';
import { GameWithDraw } from '../types/gameTypes';

const baseGame: GameWithDraw = {
  game_id: 'evt1',
  commence_time: '2026-10-26T18:15:00Z',
  completed: false,
  home: { team: 'Chicago Bears', score: null, odds: { h2h: -155, spread_point: -3, spread_price: -105 } },
  away: { team: 'New England Patriots', score: null, odds: { h2h: 130, spread_point: 3, spread_price: -118 } },
  totals: { over_point: 47.5, over_price: -110, under_point: 47.5, under_price: -115 },
};

const noOddsNoScore: GameWithDraw = {
  ...baseGame,
  home: { team: 'Chicago Bears', score: null, odds: { h2h: null, spread_point: null, spread_price: null } },
  away: { team: 'New England Patriots', score: null, odds: { h2h: null, spread_point: null, spread_price: null } },
  totals: { over_point: null, over_price: null, under_point: null, under_price: null },
};

describe('hasNoOdds', () => {
  it('is false when any odds field is posted', () => {
    expect(hasNoOdds(baseGame)).toBe(false);
  });

  it('is true when h2h/spread/totals are all null', () => {
    expect(hasNoOdds(noOddsNoScore)).toBe(true);
  });
});

describe('hasFinalScore / hasLiveScore', () => {
  it('a completed game with a score is final, not live', () => {
    const game: GameWithDraw = { ...baseGame, completed: true, home: { ...baseGame.home, score: 24 }, away: { ...baseGame.away, score: 17 } };
    expect(hasFinalScore(game)).toBe(true);
    expect(hasLiveScore(game)).toBe(false);
  });

  it('an in-progress game (scored, not completed) is live, not final', () => {
    const game: GameWithDraw = { ...baseGame, completed: false, home: { ...baseGame.home, score: 10 }, away: { ...baseGame.away, score: 7 } };
    expect(hasLiveScore(game)).toBe(true);
    expect(hasFinalScore(game)).toBe(false);
  });

  it('a scheduled game with no score yet is neither final nor live', () => {
    expect(hasFinalScore(baseGame)).toBe(false);
    expect(hasLiveScore(baseGame)).toBe(false);
  });
});

describe('shouldDisplayGame', () => {
  it('displays a game with posted odds even with no score yet', () => {
    expect(shouldDisplayGame(baseGame)).toBe(true);
  });

  it('displays a completed game even once its odds have cleared', () => {
    const game: GameWithDraw = { ...noOddsNoScore, completed: true, home: { ...noOddsNoScore.home, score: 24 }, away: { ...noOddsNoScore.away, score: 17 } };
    expect(shouldDisplayGame(game)).toBe(true);
  });

  it('hides a game with no posted odds and no score (scheduled far out)', () => {
    expect(shouldDisplayGame(noOddsNoScore)).toBe(false);
  });
});
