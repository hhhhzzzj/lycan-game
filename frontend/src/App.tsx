import { useState } from 'react';
import GameSetup from './components/GameSetup';
import GameBoard from './components/GameBoard';
import { useGameSocket } from './hooks/useGameSocket';

export default function App() {
  const [gameId, setGameId] = useState<string | null>(null);
  const { gameState, connected } = useGameSocket(gameId);

  const handleGameStarted = (id: string) => {
    setGameId(id);
  };

  if (!gameId || !gameState) {
    return <GameSetup onGameStarted={handleGameStarted} />;
  }

  return (
    <GameBoard gameState={gameState} gameId={gameId} connected={connected} />
  );
}
