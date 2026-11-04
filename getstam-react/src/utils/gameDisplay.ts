import { GameWithDraw } from "../types/gameTypes";

// A game with no posted odds anywhere (h2h/spread/totals) has nothing useful to show
// UNLESS it also has a final score (a completed game whose odds have since cleared —
// that should still display, just with the score instead of odds).
export function hasNoOdds(game: GameWithDraw): boolean {
  const { home, away, totals } = game;
  return (
    (!home.odds || (home.odds.h2h === null && home.odds.spread_point === null && home.odds.spread_price === null)) &&
    (!away.odds || (away.odds.h2h === null && away.odds.spread_point === null && away.odds.spread_price === null)) &&
    (!totals || (totals.over_point === null && totals.under_point === null && totals.over_price === null && totals.under_price === null))
  );
}

function hasScore(game: GameWithDraw): boolean {
  const { home, away } = game;
  return (
    home.score !== null && home.score !== undefined &&
    away.score !== null && away.score !== undefined
  );
}

export function hasFinalScore(game: GameWithDraw): boolean {
  return game.completed === true && hasScore(game);
}

// A game that has started (has a score) but isn't marked completed yet.
export function hasLiveScore(game: GameWithDraw): boolean {
  return game.completed !== true && hasScore(game);
}

// Single source of truth for "will the game card render this game" — exported so list
// pages (e.g. GamesPage) can filter/count consistently with what actually renders,
// instead of fetching N games, silently rendering nothing for some of them, and
// showing a misleading "N games today" count with a blank grid underneath.
export function shouldDisplayGame(game: GameWithDraw): boolean {
  return hasFinalScore(game) || hasLiveScore(game) || !hasNoOdds(game);
}
