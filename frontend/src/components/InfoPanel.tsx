import type { Player } from '../types/game';
import EventLog, { type GameEvent } from './EventLog';
import VoteChart from './VoteChart';

interface Props {
    events: GameEvent[];
    votes: Record<string, number | null>;
    players: Player[];
}

export default function InfoPanel({ events, votes, players }: Props) {
    return (
        <aside
            className="w-[300px] p-3 border-l overflow-y-auto flex flex-col"
            style={{ background: 'var(--bg-panel)', borderColor: 'var(--border)' }}
        >
            <div
                className="text-[11px] tracking-[2px] mb-2 pb-1.5 border-b"
                style={{ color: 'var(--text-muted)', borderColor: 'var(--border)' }}
            >
                📜 事件日志
            </div>
            <div className="mb-4 flex-1 overflow-y-auto">
                <EventLog events={events} />
            </div>

            <div
                className="text-[11px] tracking-[2px] mb-2 pb-1.5 border-b"
                style={{ color: 'var(--text-muted)', borderColor: 'var(--border)' }}
            >
                🗳 投票
            </div>
            <VoteChart votes={votes} players={players} />
        </aside>
    );
}
