import type { Player } from '../types/game';

interface Props {
    player: Player;
    isSpeaking: boolean;
}

const roleLabel = (role: string) => {
    switch (role) {
        case 'werewolf': return '狼人';
        case 'prophet': return '预言家';
        case 'witch': return '女巫';
        default: return '村民';
    }
};

const roleColor = (role: string) => {
    switch (role) {
        case 'werewolf': return '#e55';
        case 'prophet': return '#6af';
        case 'witch': return '#c6f';
        default: return 'var(--text-muted)';
    }
};

export default function PlayerCard({ player, isSpeaking }: Props) {
    const dead = !player.is_alive;

    return (
        <div
            className={`flex items-center gap-2.5 px-3 py-2.5 rounded transition-all duration-300 ${isSpeaking ? 'animate-breathe' : ''
                } ${dead ? 'opacity-35 grayscale-[0.6]' : ''}`}
            style={{
                background: 'var(--bg-card)',
                border: isSpeaking ? '1px solid var(--gold-dim)' : '1px solid transparent',
            }}
        >
            <div
                className="w-[26px] h-[26px] leading-[26px] text-center rounded-full text-[12px] font-bold shrink-0"
                style={{ background: 'var(--blood)', color: '#ddd' }}
            >
                {player.seat_id}
            </div>
            <div className="flex-1 min-w-0">
                <div className="text-[13px] font-bold truncate">{player.player_name}</div>
                <div className="text-[10px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
                    {player.model_name} · <span style={{ color: roleColor(player.role) }}>{roleLabel(player.role)}</span>
                </div>
            </div>
            <span className="shrink-0 text-[12px]" style={{ color: dead ? 'var(--blood-glow)' : '#4caf50' }}>
                {dead ? '✝' : '●'}
            </span>
        </div>
    );
}
