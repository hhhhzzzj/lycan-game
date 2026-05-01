import PlayerCard from './PlayerCard';
import SpeechPanel from './SpeechPanel';
import HistoryPanel from './HistoryPanel';
import NightActionPanel from './NightActionPanel';
import type { PublicGameState } from '../types/game';

interface Props {
  gameState: PublicGameState;
  gameId: string;
  connected: boolean;
  onStartGame: () => void;
}

export default function GameBoard({ gameState, gameId, connected, onStartGame }: Props) {
  const { phase, day, players, full_history, current_speaker, current_thinking, current_speech, night_info, phase_info, winner } = gameState;
  const isNight = phase === 'night';
  const isGameOver = phase === 'game_over';
  const isGameInit = phase === 'game_init';

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2>
          {isGameInit ? '等待游戏开始' : isGameOver ? '游戏结束' : `第 ${day} 天 - ${isNight ? '夜晚' : phase === 'revote' ? '重投' : '白天'}`}
        </h2>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <span style={{ padding: '4px 12px', borderRadius: 4, fontSize: 13, background: connected ? '#2e7d32' : '#c62828', color: '#fff' }}>
            {connected ? '已连接' : '断开'}
          </span>
          <span style={{ fontSize: 13, color: '#666' }}>ID: {gameId}</span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 24 }}>
        {players.map((p) => (
          <PlayerCard key={p.seat_id} player={p} isCurrentPlayer={p.seat_id === current_speaker} isSpectator={true} />
        ))}
      </div>

      {phase_info && (
        <div style={{ padding: 12, marginBottom: 16, background: phase_info.includes('胜利') ? '#1b5e20' : '#37474f', borderRadius: 8, fontSize: 16, fontWeight: 'bold', textAlign: 'center', color: '#fff' }}>
          {phase_info}
        </div>
      )}

      {isGameInit && (
        <div style={{ textAlign: 'center' }}>
          <button onClick={onStartGame} style={{ padding: '12px 32px', fontSize: 16, cursor: 'pointer' }}>开始游戏</button>
        </div>
      )}

      {isNight ? (
        <NightActionPanel nightInfo={night_info} currentThinking={current_thinking} />
      ) : (
        !isGameInit && !isGameOver && (
          <SpeechPanel currentSpeaker={current_speaker} currentThinking={current_thinking} currentSpeech={current_speech ?? null} />
        )
      )}

      <div style={{ marginTop: 24 }}>
        <HistoryPanel speechHistory={full_history} />
      </div>

      {isGameOver && winner && (
        <div style={{ marginTop: 24, padding: 24, background: '#1b5e20', borderRadius: 12, textAlign: 'center', fontSize: 24, fontWeight: 'bold', color: '#fff' }}>
          {winner === 'villager' ? '好人阵营 胜利！' : '狼人阵营 胜利！'}
        </div>
      )}
    </div>
  );
}
