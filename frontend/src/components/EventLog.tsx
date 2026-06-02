export interface GameEvent {
    text: string;
    type: 'night' | 'day' | 'vote' | 'info';
}

interface Props {
    events: GameEvent[];
}

export default function EventLog({ events }: Props) {
    const borderColor = (type: string) => {
        switch (type) {
            case 'night': return 'var(--blood)';
            case 'day': return 'var(--gold-dim)';
            case 'vote': return '#888';
            default: return 'var(--border)';
        }
    };

    if (events.length === 0) {
        return <span className="text-[11px] italic" style={{ color: 'var(--text-muted)' }}>暂无事件</span>;
    }

    return (
        <div className="flex flex-col gap-1">
            {events.map((ev, i) => (
                <div
                    key={i}
                    className="p-1.5 px-2 text-[11px] rounded animate-fade-in-up"
                    style={{
                        background: 'rgba(0,0,0,0.3)',
                        color: 'var(--text-muted)',
                        borderLeft: `2px solid ${borderColor(ev.type)}`,
                    }}
                >
                    {ev.text}
                </div>
            ))}
        </div>
    );
}
