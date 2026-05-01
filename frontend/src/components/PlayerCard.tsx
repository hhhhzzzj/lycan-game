import type { Player } from '../types/game';

interface Props {
  player: Player;
  isCurrentPlayer: boolean;
  isSpectator: boolean;
}

export default function PlayerCard({ player, isCurrentPlayer, isSpectator }: Props) {
  const statusColor = player.is_alive ? '#4caf50' : '#f44336';
  const roleLabel =
    player.role === 'werewolf' ? '狼人' :
    player.role === 'prophet' ? '预言家' :
    player.role === 'witch' ? '女巫' : '村民';
  const roleColor =
    player.role === 'werewolf' ? '#d32f2f' :
    player.role === 'prophet' ? '#1976d2' :
    player.role === 'witch' ? '#7b1fa2' : '#388e3c';

  return (
    <div style={{
      border: isCurrentPlayer ? '2px solid gold' : '1px solid #666',
      borderRadius: 8, padding: 12,
      background: player.is_alive ? '#1a1a2e' : '#2a1a1a',
      minWidth: 120, textAlign: 'center',
    }}>
      <div style={{ fontSize: 20, fontWeight: 'bold' }}>{player.seat_id}号</div>
      <div style={{ fontSize: 14 }}>{player.player_name}</div>
      {isSpectator && (
        <div style={{ marginTop: 4, padding: '2px 8px', borderRadius: 4, background: roleColor, fontSize: 12, color: '#fff' }}>
          {roleLabel}
        </div>
      )}
      <div style={{ marginTop: 4, width: 12, height: 12, borderRadius: '50%', background: statusColor, display: 'inline-block' }} />
      <div style={{ fontSize: 11 }}>{player.model_name}</div>
    </div>
  );
}
