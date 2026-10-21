import React from "react";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import GameOdds from "./GameOdds";
import { GameWithDraw } from "../types/gameTypes";

const baseGame: GameWithDraw = {
  game_id: "evt1",
  commence_time: "2026-10-26T18:15:00Z",
  completed: false,
  home: { team: "Chicago Bears", score: null, odds: { h2h: -155, spread_point: -3, spread_price: -105 } },
  away: { team: "New England Patriots", score: null, odds: { h2h: 130, spread_point: 3, spread_price: -118 } },
  totals: { over_point: 47.5, over_price: -110, under_point: 47.5, under_price: -115 },
};

function renderGame(game: GameWithDraw) {
  return render(
    <MemoryRouter>
      <GameOdds game={game} />
    </MemoryRouter>
  );
}

describe("GameOdds opening line", () => {
  it("shows the opening line alongside current odds when present", () => {
    const game: GameWithDraw = {
      ...baseGame,
      opening: {
        home: { spread_point: -7, spread_price: -110, h2h: -280 },
        away: { spread_point: 7, spread_price: -110, h2h: 230 },
        totals: { over_point: 44.5, over_price: -110, under_point: 44.5, under_price: -110 },
        snapshot_time: "2026-10-14T12:00:00Z",
      },
    };
    renderGame(game);

    expect(screen.getByText("Open -7 (-110)")).toBeInTheDocument();
    expect(screen.getByText("Open +7 (-110)")).toBeInTheDocument();
    expect(screen.getByText("Open -280")).toBeInTheDocument();
    expect(screen.getByText("Open +230")).toBeInTheDocument();
    expect(screen.getByText("Open Over +44.5 (-110)")).toBeInTheDocument();
    expect(screen.getByText("Open Under +44.5 (-110)")).toBeInTheDocument();
  });

  it("renders current odds with no Open row when opening data is absent", () => {
    renderGame(baseGame);

    expect(screen.queryByText(/^Open/)).not.toBeInTheDocument();
    expect(screen.getByText("-3 (-105)")).toBeInTheDocument();
  });
});
