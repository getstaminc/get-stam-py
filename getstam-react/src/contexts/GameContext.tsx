import React, { createContext, useContext, useState, ReactNode } from 'react';
import { LiveGameData } from '../types/gameTypes';

interface GameContextType {
  currentGame: LiveGameData | null;
  setCurrentGame: (game: LiveGameData | null) => void;
}

const GameContext = createContext<GameContextType | undefined>(undefined);

export const GameProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [currentGame, setCurrentGame] = useState<LiveGameData | null>(null);

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
