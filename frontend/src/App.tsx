import { useState } from 'react';
import GameSetup from './components/GameSetup';
import GameBoard from './components/GameBoard';
import { useGameSocket } from './hooks/useGameSocket';

const API_BASE = 'http://localhost:8000';

export default function App() {
  const [gameId, setGameId] = useState<string | null>(null);
  const { gameState, connected } = useGameSocket(gameId);

  const handleGameCreated = (id: string) => {
    setGameId(id);
  };

  const handleStartGame = async () => {
    if (!gameId) return;
    try {
      await fetch(`${API_BASE}/game/${gameId}/start`, { method: 'POST' });
    } catch (err) {
      console.error('Failed to start game', err);
    }
  };

  if (!gameId || !gameState) {
    return <GameSetup onGameCreated={handleGameCreated} />;
  }

  return (
    <GameBoard gameState={gameState} gameId={gameId} connected={connected} onStartGame={handleStartGame} />
  );
}
