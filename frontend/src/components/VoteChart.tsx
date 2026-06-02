import type { Player } from '../types/game';

interface Props {
    votes: Record<string, number | null>;
    players: Player[];
}

export default function VoteChart({ votes, players }: Props) {
    // Aggregate: count votes per target
    const tally: Record<number, { count: number; voters: number[] }> = {};
    for (const [voterSeat, targetSeat] of Object.entries(votes)) {
        if (targetSeat === null) continue;
        if (!tally[targetSeat]) tally[targetSeat] = { count: 0, voters: [] };
        tally[targetSeat].count++;
        tally[targetSeat].voters.push(Number(voterSeat));
    }

    const entries = Object.entries(tally)
        .map(([seat, data]) => ({ seat: Number(seat), ...data }))
        .sort((a, b) => b.count - a.count);

    if (entries.length === 0) {
        return <span className="text-[11px] italic" style={{ color: 'var(--text-muted)' }}>暂无投票</span>;
    }

    const maxVotes = Math.max(...entries.map(e => e.count), 1);

    return (
        <div className="flex flex-col gap-1.5">
            {entries.map(e => {
                const player = players.find(p => p.seat_id === e.seat);
                const pct = (e.count / maxVotes * 100) + '%';
                const isMax = e.count === maxVotes;
                return (
                    <div key={e.seat} className="flex items-center gap-2 animate-fade-in-up">
                        <span className="text-[11px] w-[55px] shrink-0 truncate">
                            {e.seat}号{player ? ` ${player.player_name.slice(0, 3)}` : ''}
                        </span>
                        <div className="flex-1 h-4 rounded overflow-hidden" style={{ background: 'rgba(0,0,0,0.4)' }}>
                            <div
                                className="h-full rounded transition-all duration-700"
                                style={{
                                    width: pct,
                                    background: 'linear-gradient(90deg, var(--blood), var(--blood-glow))',
                                }}
                            />
                        </div>
                        <span className="text-[11px] w-[30px] text-right" style={{ color: 'var(--text-accent)' }}>
                            {e.count}票
                        </span>
                        {isMax && (
                            <span className="text-[9px] px-1 rounded" style={{ background: 'var(--blood)', color: '#fff' }}>
                                放逐
                            </span>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
