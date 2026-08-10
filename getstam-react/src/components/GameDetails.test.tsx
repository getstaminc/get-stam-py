import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import GameDetails from "./GameDetails";

// Regression test for the bug that shipped with the SEO slug-URL change:
// GameDetails used to read the Odds-API event id from `window.location.search`
// (`?game_id=`) to fetch player props. The new slug route
// (/game-details/:sport/:slug) never sets that query param, so player props
// silently never loaded there. The fix reads the event id from the `game`
// prop instead (which is always populated regardless of URL shape).
//
// This test pins that contract: player props must fetch using `game.game_id`,
// even when the URL has no `game_id` query string at all.

const fakeMlbGame = {
  game_id: "0f350cb709d6394c946ef1df6fca40af",
  commence_time: "2026-07-29T01:41:00+00:00",
  home: { team: "Athletics", score: null, odds: {} },
  away: { team: "Boston Red Sox", score: null, odds: {} },
  totals: {},
};

function renderOnSlugRoute(game: any) {
  // No `?game_id=` in this URL at all - mirrors the real slug route.
  window.history.pushState({}, "", "/game-details/mlb/boston-red-sox-vs-athletics-2026-07-28");
  return render(
    <MemoryRouter initialEntries={["/game-details/mlb/boston-red-sox-vs-athletics-2026-07-28"]}>
      <GameDetails game={game} sportKey="baseball_mlb" />
    </MemoryRouter>
  );
}

describe("GameDetails player props game_id contract", () => {
  beforeEach(() => {
    jest.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({}),
    } as Response);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it("fetches MLB player props using game.game_id, not the URL query string", async () => {
    renderOnSlugRoute(fakeMlbGame);

    const playerPropsTab = await screen.findByRole("tab", { name: /player props/i });
    await userEvent.click(playerPropsTab);

    await waitFor(() => {
      const calls = (global.fetch as jest.Mock).mock.calls.map((c) => c[0] as string);
      const propsCall = calls.find((url) => url.includes("/api/odds/mlb/player-props/"));
      expect(propsCall).toBeDefined();
      expect(propsCall).toContain(fakeMlbGame.game_id);
    });
  });
});
