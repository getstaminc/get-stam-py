import React from "react";
import GameDetails from "../components/GameDetails";

const dummyData = {
  away: {
    odds: {
      h2h: -245,
      spread_point: -5.5,
      spread_price: -110,
    },
    score: null,
    team: "Arizona Cardinals",
  },
  commence_time: "2025-09-07T17:00:00+00:00",
  game_id: "557d13ef8f4c1d21044f3a478cda6d0b",
  home: {
    odds: {
      h2h: 200,
      spread_point: 5.5,
      spread_price: -110,
    },
    score: null,
    team: "New Orleans Saints",
  },
  isToday: false,
  totals: {
    over_point: 42.5,
    over_price: -110,
    under_point: 42.5,
    under_price: -110,
  },
};

const GameDetailsPage: React.FC = () => {
  return (
    <div>
      <GameDetails game={dummyData} />
    </div>
  );
};

export default GameDetailsPage;