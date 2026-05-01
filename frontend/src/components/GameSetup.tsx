import { useState } from 'react';
import type { PlayerConfig, ModelPreset } from '../types/game';

const API_BASE = 'http://localhost:8000';

interface Props {
  onGameCreated: (gameId: string) => void;
}

const DEFAULT_PLAYERS: PlayerConfig[] = Array.from({ length: 6 }, (_, i) => ({
  seat_id: i + 1,
  player_name: `玩家${i + 1}`,
  model_name: 'claude-sonnet-4-6-20250514',
  provider: 'anthropic',
  api_key: '',
}));

const MODEL_PRESETS: ModelPreset[] = [
  { provider: 'anthropic', name: 'Claude Sonnet 4.6', model: 'claude-sonnet-4-6-20250514', description: 'Anthropic Claude' },
  { provider: 'openai', name: 'GPT-4o', model: 'gpt-4o', description: 'OpenAI GPT-4o' },
  { provider: 'openai', name: 'GPT-4.1', model: 'gpt-4.1', description: 'OpenAI GPT-4.1' },
  { provider: 'google', name: 'Gemini 2.5 Pro', model: 'gemini-2.5-pro-exp-03-25', description: 'Google Gemini' },
];

export default function GameSetup({ onGameCreated }: Props) {
  const [players, setPlayers] = useState<PlayerConfig[]>(DEFAULT_PLAYERS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const updatePlayer = (seat: number, field: keyof PlayerConfig, value: string) => {
    setPlayers((prev) =>
      prev.map((p) => (p.seat_id === seat ? { ...p, [field]: value } : p))
    );
  };

  const handleCreateGame = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/game/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ players }),
      });
      if (!res.ok) throw new Error('Failed to create game');
      const data = await res.json();
      onGameCreated(data.game_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <h2>AI 狼人杀 - 游戏配置</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16 }}>
        {players.map((p) => (
          <div key={p.seat_id} style={{ border: '1px solid #ccc', padding: 12, borderRadius: 8 }}>
            <h3>{p.seat_id}号 - {p.player_name}</h3>
            <label>名称: <input value={p.player_name} onChange={(e) => updatePlayer(p.seat_id, 'player_name', e.target.value)} /></label>
            <br />
            <label>模型:
              <select value={p.model_name} onChange={(e) => {
                const preset = MODEL_PRESETS.find((m) => m.model === e.target.value);
                if (preset) {
                  updatePlayer(p.seat_id, 'model_name', preset.model);
                  updatePlayer(p.seat_id, 'provider', preset.provider);
                }
              }}>
                {MODEL_PRESETS.map((m) => (
                  <option key={m.model} value={m.model}>{m.name}</option>
                ))}
              </select>
            </label>
            <br />
            <label>API Key: <input type="password" value={p.api_key} onChange={(e) => updatePlayer(p.seat_id, 'api_key', e.target.value)} placeholder="sk-..." /></label>
          </div>
        ))}
      </div>
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <button onClick={handleCreateGame} disabled={loading} style={{ marginTop: 24, padding: '12px 32px', fontSize: 16 }}>
        {loading ? '创建中...' : '创建游戏'}
      </button>
    </div>
  );
}
