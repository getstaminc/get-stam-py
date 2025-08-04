import React, { createContext, useContext, useState, ReactNode } from 'react';

interface GameData {
  game_id: string;
  away: {
    odds: {
      h2h: number | null;
      spread_point: number | null;
      spread_price: number | null;
    };
    score: number | null;
    team: string;
  };
  home: {
    odds: {
      h2h: number | null;
      spread_point: number | null;
      spread_price: number | null;
    };
    score: number | null;
    team: string;
  };
  isToday: boolean;
  totals: {
    over_point: number | null;
    over_price: number | null;
    under_point: number | null;
    under_price: number | null;
  };
}

interface GameContextType {
  currentGame: GameData | null;
  setCurrentGame: (game: GameData | null) => void;
}

const GameContext = createContext<GameContextType | undefined>(undefined);

export const GameProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [currentGame, setCurrentGame] = useState<GameData | null>(null);

  return (
    <GameContext.Provider value={{ currentGame, setCurrentGame }}>
      {children}
    </GameContext.Provider>
  );
};

export const useGame = () => {
  const context = useContext(GameContext);
  if (context === undefined) {
    throw new Error('useGame must be used within a GameProvider');
  }
  return context;
};
