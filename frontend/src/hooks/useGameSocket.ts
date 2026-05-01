// frontend/src/hooks/useGameSocket.ts
import { useEffect, useRef, useState } from 'react';
import type { PublicGameState } from '../types/game';

const WS_BASE = 'ws://localhost:8000';

export function useGameSocket(gameId: string | null) {
  const [gameState, setGameState] = useState<PublicGameState | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!gameId) return;

    const ws = new WebSocket(`${WS_BASE}/game/${gameId}/ws`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as PublicGameState;
        setGameState(data);
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      setConnected(false);
    };

    ws.onerror = () => {
      setConnected(false);
    };

    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 30000);

    return () => {
      clearInterval(pingInterval);
      ws.close();
    };
  }, [gameId]);

  return { gameState, connected };
}
