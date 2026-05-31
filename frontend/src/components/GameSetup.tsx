import { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000';

interface PlayerDisplay {
  seat_id: number;
  player_name: string;
  model_name: string;
  provider: string;
  base_url?: string;
}

interface Props {
  onGameStarted: (gameId: string) => void;
}

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: 'Claude',
  openai: 'OpenAI 兼容',
  google: 'Gemini',
};

export default function GameSetup({ onGameStarted }: Props) {
  const [players, setPlayers] = useState<PlayerDisplay[]>([]);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch(`${API_BASE}/game/config`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load config');
        return res.json();
      })
      .then((data) => setPlayers(data.players))
      .catch((err) => setError(err instanceof Error ? err.message : 'Unknown error'))
      .finally(() => setLoading(false));
  }, []);

  const handleStart = async () => {
    setStarting(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/game/start`, { method: 'POST' });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to start game');
      }
      const data = await res.json();
      onGameStarted(data.game_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setStarting(false);
    }
  };

  if (loading) {
    return <div style={{ padding: 24, color: '#fff' }}>加载配置中...</div>;
  }

  return (
    <div style={{ padding: 24, maxWidth: 800, margin: '0 auto' }}>
      <h2>AI 狼人杀</h2>
      <p style={{ color: '#888', marginBottom: 24 }}>从 backend/config/players.json 读取玩家配置</p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
        {players.map((p) => (
          <div key={p.seat_id} style={{ border: '1px solid #444', padding: 12, borderRadius: 8, background: '#1a1a2e' }}>
            <h3 style={{ margin: 0 }}>{p.seat_id}号 - {p.player_name}</h3>
            <div style={{ marginTop: 4 }}>
              {PROVIDER_LABELS[p.provider] || p.provider}: {p.model_name}
            </div>
            {p.base_url && (
              <div style={{ fontSize: 12, color: '#888', marginTop: 2, wordBreak: 'break-all' }}>
                {p.base_url}
              </div>
            )}
          </div>
        ))}
      </div>

      {error && <p style={{ color: '#e57373', marginTop: 16 }}>{error}</p>}

      <button
        onClick={handleStart}
        disabled={starting || players.length === 0}
        style={{ marginTop: 24, padding: '12px 32px', fontSize: 16, cursor: 'pointer' }}
      >
        {starting ? '启动中...' : '开始游戏'}
      </button>
    </div>
  );
}
