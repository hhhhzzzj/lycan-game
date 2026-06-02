import type { Player } from '../types/game';
import PlayerCard from './PlayerCard';

interface Props {
    players: Player[];
    currentSpeaker: number | null;
}

export default function PlayerPanel({ players, currentSpeaker }: Props) {
    return (
        <aside
            className="w-[300px] p-3 border-r overflow-y-auto flex flex-col"
            style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}
        >
            <div
                className="text-[11px] tracking-[2px] mb-2 pb-1.5 border-b"
                style={{ color: 'var(--text-muted)', borderColor: 'var(--border)' }}
            >
                ⚔ 玩家
            </div>
            <div className="flex flex-col gap-1.5">
                {players.map(p => (
                    <PlayerCard key={p.seat_id} player={p} isSpeaking={p.seat_id === currentSpeaker} />
                ))}
            </div>
        </aside>
    );
}
