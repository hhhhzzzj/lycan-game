import { useState } from 'react';
import WelcomePage from './components/WelcomePage';
import GameLayout from './components/GameLayout';
import { useGameSocket } from './hooks/useGameSocket';

export default function App() {
  const [gameId, setGameId] = useState<string | null>(null);
  const { gameState, connected } = useGameSocket(gameId);

  if (!gameId || !gameState) {
    return <WelcomePage onGameStarted={setGameId} />;
  }

  return <GameLayout gameState={gameState} gameId={gameId} connected={connected} />;
}
